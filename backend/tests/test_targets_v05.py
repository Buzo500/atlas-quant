"""Independent arithmetic and real transaction/HTTP boundaries for manual targets."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from threading import Barrier
import json
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from atlas_quant import targets
from atlas_quant.app import create_app
from atlas_quant.targets_contracts import (TargetSpec, TargetDraftInput, TargetActivateInput,
    TargetEvaluationInput, TargetReport)
from atlas_quant.targets_service import TargetsService
from atlas_quant.valuation_service import ValuationService
from atlas_quant.catalog import RevisionConflict
from atlas_quant.portfolios import PortfolioService
from atlas_quant.store import UnitOfWork, Store
from test_multicurrency_d6 import setup, row, body, confirm, dump, LOCAL
from test_market_valuation_d6 import invested, import_market, market_request, bind_prices, bind_fx, nav_request

A, B = 'a'*32, 'b'*32


def allocation(ident, weight, lo='0', hi='100', cap='100'):
    return dict(instrument_id=ident, weight=weight, minimum=lo, maximum=hi, concentration_limit=cap)


def specification(rows=None):
    return dict(name='Objetivos ficticios', rows=rows or [allocation(None, '100')])


def pure_cut(values, status='complete', nav='10000'):
    return dict(status=status, exact_value=nav, reasons=[], components=[dict(kind=kind,reference=ref,
        currency=currency, native_value=value, eur_value=value) for kind,ref,currency,value in values])


CAT = dict(instruments=[dict(id=A,name='Activo A'),dict(id=B,name='Activo B')],
    listings=[dict(id='l1',instrument_id=A),dict(id='l2',instrument_id=A),dict(id='l3',instrument_id=B)])


def test_independent_10000_reference_and_same_instrument_aggregation():
    ref = json.loads((Path(__file__).parents[2]/'docs/fixtures/v0_5_objetivos.json').read_text())['cases'][0]
    spec = specification([allocation(A,'50','45','55','58'),allocation(B,'30','25','35'),allocation(None,'20','15','25')])
    value = targets.evaluate(pure_cut([('position','l1','EUR','3500'),('position','l2','EUR','2500'),
        ('position','l3','EUR','2000'),('cash','EUR','EUR','2000')]), spec, CAT, {'events':[]})
    assert [r['weight'] for r in value['rows']] == ref['weights']
    assert [r['deviation_eur'] for r in value['rows']] == ref['differences']
    assert value['rows'][0]['reasons'] == ['above_band','concentration_exceeded']
    assert value['rows'][1]['reasons'] == ['below_band']
    assert value['resources']['committed'] is None


def test_right_belongs_to_instrument_and_is_not_spendable_cash():
    cut=pure_cut([('position','l1','EUR','950'),('receivable','div','EUR','50'),('cash','EUR','EUR','1000')],nav='2000')
    result=targets.evaluate(cut,specification([allocation(A,'50'),allocation(None,'50')]),CAT,{'events':[dict(id='div',listing_id='l1')]})
    assert [r['weight'] for r in result['rows']]==['50','50']
    assert result['rows'][0]['receivable_eur']=='50'
    assert result['resources']['cash']==[dict(currency='EUR',native_amount='1000',eur_value='1000')]


@pytest.mark.parametrize('status,nav,value', [('incomplete',None,None),('complete','0','0'),('complete','-1','-1')])
def test_no_global_weights_or_deviations_for_incomplete_or_nonpositive_nav(status,nav,value):
    result=targets.evaluate(pure_cut([('cash','EUR','EUR',value)],status,nav),specification(),CAT,{'events':[]})
    assert result['status']=='unavailable'
    assert all(r['weight'] is None and r['deviation_eur'] is None for r in result['rows'])


def test_provisional_and_unplanned_holdings_are_explicit():
    result=targets.evaluate(pure_cut([('position','l1','EUR','10000')],'provisional'),specification(),CAT,{'events':[]})
    assert result['status']=='provisional' and len(result['rows'])==2
    assert result['rows'][0]['reasons']==['no_target']
    assert result['rows'][0]['target_weight']=='0' and result['rows'][0]['weight']=='100'


@pytest.mark.parametrize('rows', [
    [allocation(None,'99.999999')], [allocation(A,'100')], [allocation(None,'50'),allocation(None,'50')],
    [allocation(A,'50'),allocation(A,'25'),allocation(None,'25')],
    [allocation(None,'100','0','99')], [allocation(None,'100','101')],
    [allocation(None,'100','0','100','99')], [allocation(None,'100.000001')],
    [allocation(None,'1e2')], [allocation(None,100)],
])
def test_reject_impossible_or_ambiguous_specs(rows):
    with pytest.raises(ValidationError):TargetSpec(**specification(rows))


def request(service, store, p, cls=TargetDraftInput, **kwargs):
    return cls(expected_revision=PortfolioService(store).read(p['id'])['portfolio']['revision'],
        expected_targets_revision=service.history(p['id'])['revision'], **kwargs)


def save_review(service, p, req, action='draft'):
    preview=service.review(p['id'],req,action)
    return service.review(p['id'],req.model_copy(update={'commit':True,'preview_token':preview['preview_token']}),action)


def activate(store,p,spec=None):
    service=TargetsService(store)
    draft=save_review(service,p,request(service,store,p,spec=TargetSpec(**(spec or specification()))))['target']
    req=request(service,store,p,TargetActivateInput,target_id=draft['id'])
    save_review(service,p,req,'activate')
    return service,draft


def saved_cut(store,p):
    service=ValuationService(store)
    req=nav_request(store,p)
    preview=service.calculate(p['id'],req)
    return service.calculate(p['id'],req.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))['cut']


def test_drafts_do_not_activate_and_history_preserves_exact_spec(setup):
    store,_,p,_=setup
    service=TargetsService(store)
    req=request(service,store,p,spec=TargetSpec(**specification()))
    before=dump(store.path)
    service.review(p['id'],req,'draft')
    assert dump(store.path)==before
    draft=save_review(service,p,req)['target']
    history=service.history(p['id'])
    assert history['revision']==1 and history['active'] is None
    assert history['targets']==[draft]
    assert TargetsService(Store(store.path)).history(p['id'])==history


def test_complete_usd_cut_exact_fx_and_report_idempotence(setup):
    store,_,p,mapping=invested(setup)
    bind_prices(store,p,import_market(store,market_request(mapping))['series'])
    bind_fx(store,p,import_market(store,market_request(mapping,'fx'),'fx')['series'])
    ident=store.read(lambda w:w.catalog())['instruments'][0]['id']
    service,draft=activate(store,p,specification([allocation(ident,'40'),allocation(None,'60')]))
    cut=saved_cut(store,p)
    req=request(service,store,p,TargetEvaluationInput,cut_id=cut['id'])
    preview=service.evaluate(p['id'],req)
    TargetReport.model_validate(preview['report'])
    assert preview['report']['status']=='complete'
    assert [r['value_eur'] for r in preview['report']['rows']]==['418','568.1']
    assert sum(Decimal(r['deviation_eur']) for r in preview['report']['rows'])==0
    assert preview['report']['resources']['cash'][1 if len(preview['report']['resources']['cash'])>1 else 0]['currency']=='USD'
    commit=req.model_copy(update={'commit':True,'preview_token':preview['preview_token']})
    saved=service.evaluate(p['id'],commit)
    before=dump(store.path)
    assert service.evaluate(p['id'],commit)==saved and dump(store.path)==before
    # A new inactive draft does not change the active policy or mark old analysis obsolete.
    save_review(service,p,request(service,store,p,spec=TargetSpec(**specification())))
    assert service.report(p['id'],saved['report']['id'])['current']
    activate(store,p)
    assert not service.report(p['id'],saved['report']['id'])['current']
    assert service.report(p['id'],saved['report']['id'])['target']==draft


@pytest.mark.parametrize('mutation', ['book','prices','fx','active'])
def test_changed_context_rejects_report_confirmation(setup,mutation):
    store,books,p,mapping=invested(setup)
    prices=market_request(mapping)
    fx=market_request(mapping,'fx')
    ps=import_market(store,prices)['series']; fs=import_market(store,fx,'fx')['series']
    bind_prices(store,p,ps); bind_fx(store,p,fs)
    service,_=activate(store,p)
    cut=saved_cut(store,p)
    req=request(service,store,p,TargetEvaluationInput,cut_id=cut['id'])
    preview=service.evaluate(p['id'],req)
    if mutation=='book':confirm(books,p['id'],body(setup,[row('deposit',external_id='new-deposit',day_sequence='3',gross_amount='1.00')]))
    elif mutation=='active':activate(store,p)
    else:
        # A newly published head invalidates the context even while the portfolio
        # remains pinned to the old source version.
        original=ps if mutation=='prices' else fs
        changed=deepcopy(original); changed['version']+=1
        store.atomic(lambda w:w.save_market_version(changed))
    with pytest.raises(RevisionConflict):
        service.evaluate(p['id'],req.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))
    assert service.reports(p['id'])['reports']==[]


def test_two_simultaneous_activations_publish_exactly_one(setup,monkeypatch):
    store,_,p,_=setup
    service=TargetsService(store)
    draft=save_review(service,p,request(service,store,p,spec=TargetSpec(**specification())))['target']
    req=request(service,store,p,TargetActivateInput,target_id=draft['id'])
    preview=service.review(p['id'],req,'activate')
    commit=req.model_copy(update={'commit':True,'preview_token':preview['preview_token']})
    original=service.validate; gate=Barrier(2)
    def together(*args):original(*args);gate.wait(timeout=5)
    monkeypatch.setattr(service,'validate',together)
    def call():
        try:return service.review(p['id'],commit,'activate')['committed']
        except RevisionConflict:return False
    with ThreadPoolExecutor(2) as pool:assert sorted(pool.map(lambda _:call(),range(2)))==[False,True]
    assert service.history(p['id'])['revision']==2
    assert service.history(p['id'])['active']==draft


@pytest.mark.parametrize('operation',['draft','activate','evaluate'])
def test_audit_failure_rolls_back_every_analytical_record(setup,monkeypatch,operation):
    store,_,p,_=setup
    service,draft=activate(store,p)
    if operation=='draft': req=request(service,store,p,spec=TargetSpec(**specification()))
    elif operation=='activate': req=request(service,store,p,TargetActivateInput,target_id=draft['id'])
    else:req=request(service,store,p,TargetEvaluationInput,cut_id=saved_cut(store,p)['id'])
    call=(lambda b:service.evaluate(p['id'],b)) if operation=='evaluate' else (lambda b:service.review(p['id'],b,operation))
    preview=call(req); before=dump(store.path)
    def fail(*_args,**_kwargs):raise RuntimeError('audit failure')
    monkeypatch.setattr(UnitOfWork,'audit',fail)
    with pytest.raises(RuntimeError):call(req.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))
    assert dump(store.path)==before


def test_real_http_controls_contracts_cross_portfolio_and_legacy(setup):
    store,_,p,_=setup
    app=create_app(str(store.path.parent),run_worker=False)
    service=TargetsService(store)
    req=request(service,store,p,spec=TargetSpec(**specification())).model_dump()
    path=f'/api/v2/portfolios/{p["id"]}/targets'
    with TestClient(app) as client:
        assert client.post(path,json=req).status_code==403
        preview=client.post(path,json=req,headers=LOCAL)
        assert preview.status_code==200,preview.text
        assert client.post(path,json={**req,'commit':True,'preview_token':'0'*64},headers=LOCAL).status_code==409
        saved=client.post(path,json={**req,'commit':True,'preview_token':preview.json()['preview_token']},headers=LOCAL)
        assert saved.status_code==200,saved.text
        other=PortfolioService(store).create('Otra','atlas-accounting-v2')
        invalid=dict(expected_revision=1,expected_targets_revision=0,target_id=saved.json()['target']['id'])
        assert client.post(f'/api/v2/portfolios/{other["id"]}/targets/activate',json=invalid,headers=LOCAL).status_code==404
        legacy=PortfolioService(store).create('Heredada','legacy-eur-v1')
        before=dump(store.path)
        assert client.get(f'/api/v2/portfolios/{legacy["id"]}/targets').status_code==422
        assert dump(store.path)==before


def test_changed_context_during_pure_calculation_is_rejected(setup,monkeypatch):
    store,_,p,_=setup
    service,_=activate(store,p)
    req=request(service,store,p,TargetEvaluationInput,cut_id=saved_cut(store,p)['id'])
    original=targets.evaluate
    def change(*args):
        value=original(*args)
        activate(store,p)
        return value
    monkeypatch.setattr(targets,'evaluate',change)
    with pytest.raises(RevisionConflict):service.evaluate(p['id'],req)
    assert service.reports(p['id'])['reports']==[]


def test_backup_restore_preserves_targets_active_pointer_and_exact_report(setup,tmp_path):
    from atlas_quant.backup import create_backup, restore_backup
    from tools.atlas_runtime import InstanceLock
    store,_,p,_=setup
    service,_=activate(store,p)
    req=request(service,store,p,TargetEvaluationInput,cut_id=saved_cut(store,p)['id'])
    preview=service.evaluate(p['id'],req)
    report=service.evaluate(p['id'],req.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))['report']
    before=dump(store.path)
    folder=create_backup(store.path,tmp_path/'backups')
    destination=tmp_path/'restored'/'atlas.sqlite3'
    restore_backup(folder,destination,tmp_path/'before',instance_lock=InstanceLock(tmp_path/'restore.lock'))
    restored=TargetsService(Store(destination))
    assert restored.history(p['id'])==service.history(p['id'])
    assert restored.report(p['id'],report['id'])==service.report(p['id'],report['id'])
    assert dump(store.path)==before

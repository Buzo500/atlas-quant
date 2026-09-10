"""Independent money conservation, currency, temporal and transaction examples."""
from copy import deepcopy
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from atlas_quant import planning
from atlas_quant.planning_contracts import PlanningInput, PlanningReport
from atlas_quant.planning_service import PlanningService
from atlas_quant.targets_contracts import TargetSpec
from atlas_quant.targets_service import TargetsService
from atlas_quant.performance_contracts import PerformanceInput
from atlas_quant.performance_service import PerformanceService
from atlas_quant.catalog import RevisionConflict
from atlas_quant.app import create_app
from atlas_quant.store import UnitOfWork, Store
from test_multicurrency_d6 import setup, dump, LOCAL, confirm, body as book_body, row
from test_market_valuation_d6 import invested, bind_prices, bind_fx, import_market, market_request
from test_targets_v05 import activate, saved_cut, allocation, specification, request, save_review

A,L='a'*32,'b'*32


def inputs(**kwargs):
    return PlanningInput(expected_revision=1,expected_targets_revision=2,**kwargs)


def rule(listing=L,**kwargs):
    return dict(listing_id=listing,quantity_step='1',fixed_fee='0',fee_bps='0',priority=0,**kwargs)


def fixture(nav='1000',position='400',cash='600',currency='EUR',target='80',fee='0',contribution='0',existing=True):
    catalog=dict(instruments=[dict(id=A,name='Activo')],listings=[dict(id=L,instrument_id=A,currency=currency)])
    spec=specification([allocation(A,target),allocation(None,str(100-D(target)))])
    cut=dict(id='c'*64,status='complete',exact_value=nav,reasons=[],components=[
        dict(kind='position',reference=L,currency=currency,native_value=position,eur_value=position,quantity=str(D(position)/100)),
        dict(kind='cash',reference=currency,currency=currency,native_value=cash,eur_value=cash)])
    mark=dict(value='100',status='complete')
    market=dict(prices={L:dict(price=mark)},fx=dict(value='1',status='complete'))
    rules=[dict(rule(),fixed_fee=fee)]
    body=inputs(kind='allocation',cut_id='c'*64,rules=rules,contribution_eur=contribution,use_existing_cash=existing)
    return cut,dict(spec=spec),None,catalog,dict(events=[]),body,market


def test_contribution_lots_fees_and_remaining_cash_independent():
    args=fixture(fee='1',contribution='250',existing=False)
    before=deepcopy(args[0])
    result=planning.allocation(*args)['variants'][0]
    assert result['trades'][0]['quantity']=='2'
    assert result['trades'][0]['fee_native']=='1'
    assert result['cash'][0]['final']=='649'
    assert result['nav_after']=='1249' and result['costs_eur']=='1'
    assert sum(D(r['value_eur']) for r in result['rows'])==D('1249')
    assert args[0]==before


def test_exact_affordability_zero_fee_does_not_drop_a_lot():
    args=fixture(nav='100',position='0',cash='100',target='100')
    result=planning.allocation(*args)['variants'][0]
    assert result['trades'][0]['quantity']=='1' and result['cash'][0]['final']=='0'


def test_native_cash_cannot_finance_another_currency():
    args=fixture(currency='USD',existing=False,contribution='1000')
    result=planning.allocation(*args)['variants'][0]
    assert result['trades']==[]
    assert result['cash']==[dict(currency='EUR',initial='0',contribution='1000',final='1000'),dict(currency='USD',initial='600',contribution='0',final='600')]


def test_rebalance_sells_only_excess_and_keeps_cash_conditional():
    args=fixture(position='900',cash='100',target='40',existing=False)
    result=planning.allocation(*args)
    assert result['variants'][0]['trades']==[]
    sells=result['variants'][1]['trades']
    assert len(sells)==1 and sells[0]['side']=='sell' and sells[0]['quantity']=='5'
    assert result['variants'][1]['cash'][0]['final']=='600'
    assert result['sale_proceeds']=='hypothetical_settled' and result['reservation_status']=='not_implemented'


def test_final_limits_fail_closed_after_fees():
    args=fixture(fee='1')
    args[1]['spec']['rows'][0].update(minimum='80',maximum='80',concentration_limit='80')
    value=planning.allocation(*args)['variants'][0]
    assert value['status']=='conflicts' and value['reasons']


def test_fee_rounding_tiny_lots_conserves_money():
    args=list(fixture(nav='1',position='0',cash='1',target='100'))
    args[5]=args[5].model_copy(update={'rules':[type(args[5].rules[0])(**dict(rule(),quantity_step='0.000001',fixed_fee='0.001',fee_bps='1'))]})
    result=planning.allocation(*args)['variants'][0]
    assert D(result['cash'][0]['final'])>=0
    assert D(result['costs_eur'])==D('.01')
    assert sum(D(r['value_eur']) for r in result['rows'])+D(result['costs_eur'])==1


@pytest.mark.parametrize('change',[dict(status='incomplete',exact_value=None),dict(exact_value='0'),dict(exact_value='-1')])
def test_unavailable_nav_produces_no_trades(change):
    args=fixture();args[0].update(change)
    result=planning.allocation(*args)
    assert all(v['status']=='unavailable' and not v['trades'] for v in result['variants'])


def test_missing_mark_blocks_entire_simulation():
    args=fixture();args[-1]['prices']={}
    assert all(v['status']=='unavailable' and not v['trades'] for v in planning.allocation(*args)['variants'])


def test_combined_shared_instrument_has_one_budget_and_residual_cash():
    active=dict(spec=specification([allocation(A,'50'),allocation(None,'50')]))
    contributors=[dict(target=dict(spec=specification([allocation(A,'80'),allocation(None,'20')])),budget='50'),
                  dict(target=dict(spec=specification([allocation(A,'20'),allocation(None,'80')])),budget='25')]
    result=planning.combine(active,contributors)
    assert [r['weight'] for r in result['spec']['rows']]==['45','55']
    assert result['unassigned_budget']=='25'
    active['spec']['rows'][0]['concentration_limit']='40'
    with pytest.raises(ValueError,match='límites'): planning.combine(active,contributors)


def test_scenario_price_fx_product_and_receivable_not_shocked_by_price():
    args=fixture(nav='1100',currency='USD')
    cut,target,_,catalog,corporate,_,_=args
    cut['components'].append(dict(kind='receivable',reference='event',currency='USD',native_value='100',eur_value='100'))
    corporate['events']=[dict(id='event',listing_id=L)]
    body=inputs(kind='scenario',cut_id='c'*64,price_shocks=[dict(instrument_id=A,change_percent='-10')],usd_eur_change_percent='5')
    result=planning.scenario(cut,target,catalog,corporate,body)
    # Asset 400*.9*1.05=378, cash 630, accrued right 105 -> 1113.
    assert result['nav_after']=='1113' and result['change_eur']=='13'
    assert result['rows'][0]['receivable_eur']=='105'


def benchmark_input(csv='date,value\n2026-01-01,100\n2026-01-02,110\n2026-01-03,99\n'):
    return inputs(kind='benchmark',performance_id='d'*64,benchmark_name='Referencia ficticia',benchmark_source='Fixture de pruebas',benchmark_csv=csv,benchmark_basis_confirmed=True)


def perf():
    return dict(id='d'*64,start_date='2026-01-01',end_date='2026-01-03',twr=dict(value='-0.01',status='complete',start_date='2026-01-01'),points=[dict(date='2026-01-01',twr_factor=None),dict(date='2026-01-02',twr_factor='1.1'),dict(date='2026-01-03',twr_factor='0.9')])


def test_benchmark_compounds_daily_returns_not_nav_flows():
    value=planning.benchmark(perf(),benchmark_input())
    assert value['excess_pp']=='0' and value['portfolio_return']=='-0.01'
    assert [p['portfolio_index'] for p in value['points']]==['100','110','99']


@pytest.mark.parametrize('csv',[
    'date,value\n2026-01-01,1\n','date,value\n2026-01-01,1\n2026-01-01,2\n',
    'date,value\n2026-01-01,NaN\n','date,value\n2026-01-01,-1\n',
    'date,close\n2026-01-01,1\n','date,value\n2026-01-01,1,extra\n',
    'date,value\n2026-01-01\n','date,value\n2026-99-99,1\n'])
def test_reject_incomparable_benchmark(csv):
    with pytest.raises(ValueError):planning.benchmark(perf(),benchmark_input(csv))


@pytest.mark.parametrize('change',[dict(contribution_eur='-1'),dict(usd_eur_change_percent='-100'),dict(rules=[dict(rule(),quantity_step='0')]),dict(rules=[dict(rule(),fee_bps='1001')]),dict(strategies=[dict(target_id='d'*64,budget='101')])])
def test_invalid_planning_inputs(change):
    with pytest.raises(ValidationError): inputs(**(dict(kind='allocation',cut_id='c'*64,rules=[rule()])|change))


def prepared(setup):
    store,books,p,mapping=invested(setup)
    bind_prices(store,p,import_market(store,market_request(mapping))['series'])
    bind_fx(store,p,import_market(store,market_request(mapping,'fx'),'fx')['series'])
    ident=store.read(lambda w:w.catalog())['instruments'][0]['id']
    _,active=activate(store,p,specification([allocation(ident,'80'),allocation(None,'20')]))
    cut=saved_cut(store,p)
    req=PlanningInput(kind='allocation',expected_revision=cut['portfolio_revision'],expected_targets_revision=2,cut_id=cut['id'],
        contribution_usd='250',rules=[dict(rule(mapping['USD']),fixed_fee='1')])
    return store,books,p,mapping,active,cut,req


def test_service_saved_report_current_idempotent_and_no_book_writes(setup):
    store,_,p,_,_,_,req=prepared(setup)
    service=PlanningService(store)
    before=dump(store.path)
    preview=service.calculate(p['id'],req)
    PlanningReport.model_validate(preview['report'])
    assert dump(store.path)==before
    commit=req.model_copy(update=dict(commit=True,preview_token=preview['preview_token']))
    saved=service.calculate(p['id'],commit)
    assert saved['report']['saved']
    after=dump(store.path)
    assert service.calculate(p['id'],commit)==saved and dump(store.path)==after
    assert PlanningService(Store(store.path)).report(p['id'],saved['report']['id'])==saved['report']
    assert len(service.history(p['id'])['reports'])==1


@pytest.mark.parametrize('mutation',['book','active','prices','fx'])
def test_stale_confirmation_rejected_and_history_retained(setup,mutation):
    store,books,p,mapping,_,_,req=prepared(setup)
    service=PlanningService(store);preview=service.calculate(p['id'],req)
    commit=req.model_copy(update=dict(commit=True,preview_token=preview['preview_token']))
    saved=service.calculate(p['id'],commit)
    if mutation=='book':confirm(books,p['id'],book_body((store,books,p,mapping),[row('deposit',external_id='new-deposit',date='2026-01-07',gross_amount='1.00',currency='EUR')]))
    elif mutation=='active':activate(store,p)
    else:
        kind='fx' if mutation=='fx' else 'prices'
        head=store.read(lambda w:w.market_list())[1 if kind=='fx' else 0]
        request=market_request(mapping,kind,days=['2026-01-05','2026-01-06','2026-01-07'],values=['0.9','0.95','0.96'] if kind=='fx' else ['100','110','111'])
        import_market(store,request.model_copy(update=dict(series_id=head['id'],expected_version=head['version'],revise_history=True,reason='Ampliar calendario de fixture')),kind)
    with pytest.raises(RevisionConflict):service.calculate(p['id'],commit)
    assert not service.report(p['id'],saved['report']['id'])['current']


def test_audit_failure_rolls_back_report_and_summary(setup,monkeypatch):
    store,_,p,_,_,_,req=prepared(setup)
    service=PlanningService(store);preview=service.calculate(p['id'],req)
    original=UnitOfWork.audit
    def fail(self,action,*args):
        if action=='planning.saved': raise RuntimeError('audit failure')
        return original(self,action,*args)
    monkeypatch.setattr(UnitOfWork,'audit',fail)
    before=dump(store.path)
    with pytest.raises(RuntimeError):service.calculate(p['id'],req.model_copy(update=dict(commit=True,preview_token=preview['preview_token'])))
    assert dump(store.path)==before


def test_concurrent_save_publishes_once(setup):
    store,_,p,_,_,_,req=prepared(setup)
    service=PlanningService(store);preview=service.calculate(p['id'],req)
    commit=req.model_copy(update=dict(commit=True,preview_token=preview['preview_token']))
    gate=Barrier(2)
    def save():gate.wait();return service.calculate(p['id'],commit)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:save(),range(2)))
    assert results[0]==results[1] and len(service.history(p['id'])['reports'])==1


def test_api_guards_schema_and_cross_portfolio_access(setup):
    store,_,p,_,_,_,req=prepared(setup)
    with TestClient(create_app(store.path.parent,run_worker=False)) as client:
        route=f'/api/v2/portfolios/{p["id"]}/planning-reports'
        assert client.post(route,json=req.model_dump()).status_code==403
        reply=client.post(route,json=req.model_dump(),headers=LOCAL)
        assert reply.status_code==200,reply.text
        assert client.get('/api/v2/portfolios/'+'0'*32+'/planning-reports/'+reply.json()['report']['id']).status_code==404


def test_real_d7_comparison_and_scenario_report_contracts(setup):
    store,_,p,_,active,cut,req=prepared(setup)
    performance=PerformanceService(store)
    body=PerformanceInput(expected_revision=cut['portfolio_revision'],start_date='2026-01-05',end_date='2026-01-06')
    preview=performance.calculate(p['id'],body)
    value=performance.calculate(p['id'],body.model_copy(update=dict(commit=True,preview_token=preview['preview_token'])))['report']
    service=PlanningService(store)
    bench=benchmark_input('date,value\n2026-01-05,100\n2026-01-06,110\n').model_copy(update=dict(expected_revision=cut['portfolio_revision'],performance_id=value['id']))
    PlanningReport.model_validate(service.calculate(p['id'],bench)['report'])
    scenario=PlanningInput(kind='scenario',cut_id=cut['id'],expected_revision=cut['portfolio_revision'],expected_targets_revision=2,usd_eur_change_percent='5')
    PlanningReport.model_validate(service.calculate(p['id'],scenario)['report'])
    aggregate=PlanningInput(kind='aggregate',expected_revision=cut['portfolio_revision'],expected_targets_revision=2,strategies=[dict(target_id=active['id'],budget='50')])
    PlanningReport.model_validate(service.calculate(p['id'],aggregate)['report'])


def test_backup_restore_preserves_all_four_analyses(setup,tmp_path):
    from atlas_quant.backup import create_backup,restore_backup
    from tools.atlas_runtime import InstanceLock
    store,_,p,_,active,cut,req=prepared(setup)
    service=PlanningService(store)
    requests=[req,PlanningInput(kind='scenario',cut_id=cut['id'],expected_revision=cut['portfolio_revision'],expected_targets_revision=2,usd_eur_change_percent='5'),
        PlanningInput(kind='aggregate',expected_revision=cut['portfolio_revision'],expected_targets_revision=2,strategies=[dict(target_id=active['id'],budget='50')])]
    perf_service=PerformanceService(store)
    perf_req=PerformanceInput(expected_revision=cut['portfolio_revision'],start_date='2026-01-05',end_date='2026-01-06')
    perf_preview=perf_service.calculate(p['id'],perf_req)
    perf_report=perf_service.calculate(p['id'],perf_req.model_copy(update=dict(commit=True,preview_token=perf_preview['preview_token'])))['report']
    requests.append(benchmark_input('date,value\n2026-01-05,100\n2026-01-06,110\n').model_copy(update=dict(expected_revision=cut['portfolio_revision'],performance_id=perf_report['id'])))
    saved=[]
    for body in requests:
        preview=service.calculate(p['id'],body)
        saved.append(service.calculate(p['id'],body.model_copy(update=dict(commit=True,preview_token=preview['preview_token'])))['report'])
    before=dump(store.path)
    backup=create_backup(store.path,tmp_path/'backups')
    destination=tmp_path/'restored'/'atlas.sqlite3'
    restore_backup(backup,destination,tmp_path/'before',instance_lock=InstanceLock(tmp_path/'restore.lock'))
    restored=PlanningService(Store(destination))
    assert restored.history(p['id'])==service.history(p['id'])
    assert [restored.report(p['id'],r['id']) for r in saved]==saved
    assert dump(store.path)==before


def test_book_change_during_calculation_cannot_publish_old_context(setup,monkeypatch):
    store,_,p,_,_,_,req=prepared(setup)
    original=planning.allocation
    def change(*args):
        result=original(*args)
        activate(store,p)
        return result
    monkeypatch.setattr(planning,'allocation',change)
    with pytest.raises(RevisionConflict):PlanningService(store).calculate(p['id'],req)
    assert PlanningService(store).history(p['id'])['reports']==[]


def test_shared_native_cash_is_spent_once_in_explicit_priority_order():
    args=list(fixture(nav='100',position='0',cash='100',target='50',existing=False,contribution='100'))
    other,other_listing='c'*32,'d'*32
    args[3]['instruments'].append(dict(id=other,name='Segundo'))
    args[3]['listings'].append(dict(id=other_listing,instrument_id=other,currency='EUR'))
    args[1]['spec']['rows']=[allocation(A,'50'),allocation(other,'50'),allocation(None,'0')]
    args[-1]['prices'][L]['price']['value']='1'
    args[-1]['prices'][other_listing]=dict(price=dict(value='1',status='complete'))
    args[5]=PlanningInput(**(args[5].model_dump()|dict(rules=[dict(rule(),priority=2),dict(rule(other_listing),priority=1)])))
    result=planning.allocation(*args)['variants'][0]
    assert [(t['instrument_id'],t['quantity']) for t in result['trades']]==[(other,'100')]
    assert result['cash'][0]['final']=='100'


@pytest.mark.parametrize('kwargs',[
    dict(kind='scenario',cut_id='c'*64,contribution_eur='10'),
    dict(kind='allocation',cut_id='c'*64,usd_eur_change_percent='5'),
    dict(kind='aggregate',cut_id='c'*64,strategies=[dict(target_id='d'*64,budget='100')]),
    dict(kind='scenario',cut_id='c'*64,strategies=[dict(target_id='d'*64,budget='50')]),
])
def test_reject_fields_that_would_be_silently_ignored(kwargs):
    with pytest.raises(ValidationError):inputs(**kwargs)


"""Independent price/FX, aligned intervals, and immutable analytical boundaries."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from atlas_quant import asset_analysis as analysis
from atlas_quant.asset_analysis_contracts import AssetAnalysisInput, AssetAnalysisReport, AssetSourceCatalog
from atlas_quant.asset_analysis_service import AssetAnalysisService
from atlas_quant.asset_analysis import calculate
from atlas_quant.catalog import RevisionConflict
from atlas_quant.app import create_app
from atlas_quant.store import UnitOfWork
from test_multicurrency_d6 import setup, dump, LOCAL
from test_market_valuation_d6 import market_request, import_market


def source(ident='A',currency='EUR',prices=None,fx=False):
    prices=prices or ['100','110','99']
    days=[(date(2026,1,1)+timedelta(days=i)).isoformat() for i in range(len(prices))]
    symbol='USD_EUR' if fx else ident
    data=dict(id=ident,name=ident,source='Fixture sintético',version=1,currency=currency,sha256='a'*64,
        bars=[dict(date=d,symbol=symbol,close=p,rate=p,available_at=d+'T21:00:00Z') for d,p in zip(days,prices)],
        quality_evidence={symbol:dict(price_basis='raw',basis_verified=True,
            calendar=dict(verified=True,start=days[0],end=days[-1],days={d:dict(status='open',close_at=d+'T20:00:00Z') for d in days}))})
    descriptor=dict(key=ident,ref=dict(kind='native',id=ident,version=1,symbol=symbol),name=ident,dataset_name=ident,
        source='Fixture sintético',instrument_id=ident,listing_id=ident,instrument_type='equity',market='TEST',currency=currency,
        sha256='a'*64,date_min=days[0],date_max=days[-1],row_count=len(prices))
    return descriptor,data


def request(sources,**updates):
    return AssetAnalysisInput(**dict(sources=[s['ref'] for s,_ in sources],start_date='2026-01-01',end_date=sources[0][1]['bars'][-1]['date'],**updates))


def run(sources,fx=None,events=None):
    return calculate(sources,fx,None,dict(events=events or []),request(sources))


def test_independent_fx_price_and_drawdown_numbers():
    result=run([source('A','USD',['100','110','99'])],source('FX',prices=['.9','.95','1'],fx=True)[1])
    p=result['profiles'][0]
    assert p['status']=='complete' and p['price_change_pct']=='10'
    assert p['max_drawdown_pct']=='-5.263157894737'
    assert p['last_close_eur']=='99'
    result=run([source('A','USD',['100','110'])],source('FX',prices=['.9','.95'],fx=True)[1])
    assert result['profiles'][0]['price_change_pct']=='16.111111111111'


def test_usd_constant_price_still_has_fx_risk():
    p=run([source('A','USD',['100','100','100'])],source('FX',prices=['.9','.95','1'],fx=True)[1])['profiles'][0]
    assert p['price_change_pct']=='11.111111111111'
    assert p['session_volatility_pct'] is not None


def test_sample_volatility_and_drawdown_independently():
    p=run([source()])['profiles'][0]
    # Simple returns +.1 and -.1: sample deviation sqrt(.02), not population .1.
    assert p['session_volatility_pct']=='14.142135623731'
    assert p['annualized_volatility_pct']=='224.499443206436'
    assert p['max_drawdown_pct']=='-10' and p['price_change_pct']=='-1'


def sequence(inverse=False):
    values=[D('100')]
    for i in range(24):
        change=D('.1') if i%2 else D('-.1')
        values.append(values[-1]*(1-change if inverse else 1+change))
    return [str(v) for v in values]


def test_pearson_on_same_returns_sample_positive_negative_constant():
    sources=[source('A',prices=sequence()),source('B',prices=sequence(True)),source('C',prices=['100']*25)]
    result=run(sources)['correlations']
    cells={(v['left'],v['right']):v for v in result['cells']}
    assert result['observations']==24
    assert cells['A','A']['value']=='1' and cells['A','B']['value']=='-1'
    assert cells['B','A']==dict(left='B',right='A',value='-1',reason=None)
    assert cells['C','C']['value'] is None and cells['C','C']['reason']=='constant_return_series'


def test_one_common_listwise_sample_and_no_bridge_over_missing_session():
    a,b,c=source('A',prices=sequence()),source('B',prices=sequence()),source('C',prices=sequence())
    b[1]['bars'].pop(8)
    c[1]['bars'].pop(12)
    result=run([a,b,c])
    assert result['correlations']['observations']==20
    intervals={(i['start_date'],i['end_date']) for i in result['correlations']['intervals']}
    assert ('2026-01-08','2026-01-10') not in intervals
    assert all(cell['value']=='1' for cell in result['correlations']['cells'])
    assert result['profiles'][1]['price_change_pct'] is None
    assert result['profiles'][1]['status']=='partial'


@pytest.mark.parametrize('fault',['basis','calendar','split','fx','available','closed'])
def test_invalid_or_missing_evidence_does_not_become_zero(fault):
    item=source('A','USD')
    fx=source('FX',prices=['1','1','1'],fx=True)[1]
    events=[]
    if fault=='basis': item[1]['quality_evidence']['A']['basis_verified']=False
    if fault=='calendar': item[1]['quality_evidence']['A']['calendar']['verified']=False
    if fault=='split': events=[dict(listing_id='A',event_type='split',effective_date='2026-01-02',cancelled=False)]
    if fault=='fx': fx['bars'].pop(1)
    if fault=='available': item[1]['bars'][1]['available_at']='2026-01-03T00:00:00Z'
    if fault=='closed': item[1]['quality_evidence']['A']['calendar']['days']['2026-01-02']['status']='closed'
    result=run([item],fx,events)
    assert result['profiles'][0]['price_change_pct'] is None
    assert result['profiles'][0]['reasons']
    assert all(c['value'] is None for c in result['correlations']['cells'])


def test_common_price_comparison_discloses_actual_dates():
    a,b=source('A'),source('B')
    b[1]['bars'].pop(0)
    r=run([a,b])['comparison']
    assert (r['start_date'],r['end_date'])==('2026-01-02','2026-01-03')
    assert r['points'][0]['indices']==['100','100']
    assert r['rows'][0]['price_change_pct']=='-10'
    assert 'partial_source_coverage' in r['reasons']


def prepare(setup):
    store,_,_,mapping=setup
    prices=import_market(store,market_request(mapping))['series']
    fx=import_market(store,market_request(mapping,'fx'),'fx')['series']
    service=AssetAnalysisService(store)
    catalog=service.catalog()
    AssetSourceCatalog.model_validate(catalog)
    body=AssetAnalysisInput(sources=[catalog['sources'][0]['ref']],fx=dict(id=fx['id'],version=fx['version']),start_date='2026-01-05',end_date='2026-01-06')
    return service,body,prices


def test_typed_review_save_idempotency_no_book_writes(setup):
    service,body,_=prepare(setup)
    before=dump(setup[0].path)
    preview=service.calculate(body)
    assert dump(setup[0].path)==before
    AssetAnalysisReport.model_validate(preview['report'])
    assert preview['report']['result']['profiles'][0]['price_change_pct']=='16.111111111111'
    commit=body.model_copy(update=dict(commit=True,preview_token=preview['preview_token']))
    first=service.calculate(commit)
    after=dump(setup[0].path)
    assert service.calculate(commit)==first and dump(setup[0].path)==after
    assert service.history()['reports'][0]['id']==first['report']['id']
    assert service.report(first['report']['id'])['current']
    for table in before:
        if table not in ('records','audit','sqlite_sequence'):
            assert before[table]==after[table]
    assert set(before['records']) <= set(after['records'])
    assert {r[0] for r in set(after['records'])-set(before['records'])}=={'asset_analysis','asset_analysis_summary'}
    assert dict(after['sqlite_sequence'])['audit']==dict(before['sqlite_sequence'])['audit']+1


def test_atomic_audit_rollback(setup,monkeypatch):
    service,body,_=prepare(setup)
    preview=service.calculate(body)
    before=dump(setup[0].path)
    def fail(*args,**kwargs): raise RuntimeError('audit unavailable')
    monkeypatch.setattr(UnitOfWork,'audit',fail)
    with pytest.raises(RuntimeError):
        service.calculate(body.model_copy(update=dict(commit=True,preview_token=preview['preview_token'])))
    assert dump(setup[0].path)==before


def test_source_revision_rejects_stale_confirmation_and_marks_history(setup):
    service,body,prices=prepare(setup)
    preview=service.calculate(body)
    committed=body.model_copy(update=dict(commit=True,preview_token=preview['preview_token']))
    saved=service.calculate(committed)['report']
    def change(work):
        head=work.get('native_price',prices['id'])
        head['version']+=1
        work.save_market_version(head)
    setup[0].atomic(change)
    with pytest.raises(RevisionConflict): service.calculate(committed)
    assert not service.report(saved['id'])['current']


def test_change_during_calculation_rejects_without_partial_publish(setup,monkeypatch):
    service,body,_=prepare(setup)
    calculate_before=analysis.calculate
    def changed(*args):
        result=calculate_before(*args)
        setup[0].atomic(lambda w:w.save_catalog_revision())
        return result
    monkeypatch.setattr(analysis,'calculate',changed)
    with pytest.raises(RevisionConflict): service.calculate(body)
    assert service.history()['reports']==[]


def test_concurrent_identical_save_is_one_report(setup,monkeypatch):
    service,body,_=prepare(setup)
    preview=service.calculate(body)
    body=body.model_copy(update=dict(commit=True,preview_token=preview['preview_token']))
    barrier=Barrier(2)
    original=analysis.calculate
    def coordinated(*args):
        result=original(*args)
        barrier.wait(timeout=10)
        return result
    monkeypatch.setattr(analysis,'calculate',coordinated)
    with ThreadPoolExecutor(2) as pool:
        values=list(pool.map(lambda _:service.calculate(body),range(2)))
    assert values[0]==values[1] and len(service.history()['reports'])==1


def test_http_guards_and_invalid_selection(setup):
    service,body,_=prepare(setup)
    app=create_app(setup[0].path.parent)
    with TestClient(app) as client:
        path='/api/v2/asset-analysis/reports'
        assert client.post(path,json=body.model_dump()).status_code==403
        assert client.post(path,json=body.model_dump(),headers=LOCAL).status_code==200
        assert client.get('/api/v2/asset-analysis/sources').status_code==200
        assert client.get(path+'/absent').status_code==404
        assert client.get(path+'?limit=101').status_code==422
    with pytest.raises(ValidationError):
        AssetAnalysisInput.model_validate(dict(body.model_dump(),sources=body.model_dump()['sources']*2))


def test_inputs_and_calculation_do_not_mutate_sources():
    sources=[source()]
    old=deepcopy(sources)
    run(sources)
    assert sources==old


def test_backup_restore_preserves_report_and_history(setup,tmp_path):
    from atlas_quant.backup import create_backup, restore_backup
    from atlas_quant.store import Store
    from tools.atlas_runtime import InstanceLock
    service,body,_=prepare(setup)
    preview=service.calculate(body)
    saved=service.calculate(body.model_copy(update=dict(commit=True,preview_token=preview['preview_token'])))['report']
    before=dump(setup[0].path)
    backup=create_backup(setup[0].path,tmp_path/'backups')
    destination=tmp_path/'restored'/'atlas.sqlite3'
    restore_backup(backup,destination,tmp_path/'before',instance_lock=InstanceLock(tmp_path/'restore.lock'))
    restored=AssetAnalysisService(Store(destination))
    assert restored.report(saved['id'])==saved and restored.history()==service.history()
    assert dump(setup[0].path)==before


def test_different_calendars_never_correlate_different_duration_returns():
    a,b=source('A'),source('B')
    b[1]['quality_evidence']['B']['calendar']['days']['2026-01-02']['status']='closed'
    b[1]['bars'].pop(1)
    result=run([a,b])
    assert all(p['status']=='complete' for p in result['profiles'])
    assert result['correlations']['observations']==0


def test_legacy_dividend_is_excluded_but_split_blocks_raw_comparison():
    item=source()
    item[1]['corporate_actions']=[dict(symbol='A',date='2026-01-02',kind='dividend',value=1)]
    assert run([item])['profiles'][0]['price_change_pct']=='-1'
    item[1]['corporate_actions'][0]['kind']='split'
    assert run([item])['profiles'][0]['price_change_pct'] is None


def test_input_limits_and_in_progress_utc_day_rejected():
    from datetime import datetime, timezone
    data=request([source()]).model_dump()
    for updates in [dict(start_date='2026-01-03'),dict(start_date='2000-01-01'),
                    dict(end_date=datetime.now(timezone.utc).date().isoformat()),
                    dict(start_date='20260101'),dict(sources=[])]:
        with pytest.raises(ValidationError): AssetAnalysisInput.model_validate(dict(data,**updates))


def test_bar_budget_rejects_before_loading_source_bodies(setup,monkeypatch):
    service,body,_=prepare(setup)
    monkeypatch.setattr(UnitOfWork,'analysis_version_size',lambda *args:200_001)
    def fail(*args): raise AssertionError('oversized payload must not be loaded')
    monkeypatch.setattr(UnitOfWork,'dataset_version',fail)
    with pytest.raises(ValueError,match='200.000'): service.calculate(body)


def test_legacy_catalog_and_version_context_are_preserved(setup):
    from atlas_quant.data import demo_dataset
    store=setup[0]
    dataset=store.atomic(lambda w:w.save_dataset(demo_dataset()))
    service=AssetAnalysisService(store)
    catalog=AssetSourceCatalog.model_validate(service.catalog())
    selected=catalog.sources[0]
    assert selected.ref.kind=='legacy' and selected.currency=='EUR'
    body=AssetAnalysisInput(sources=[selected.ref],start_date=selected.date_min,end_date=(date.fromisoformat(selected.date_max)-timedelta(days=1)).isoformat())
    before=dump(store.path)
    result=service.calculate(body)
    assert result['report']['result']['profiles'][0]['status']=='unavailable'
    assert dump(store.path)==before
    # Updating the same source head preserves the old version but invalidates its old review.
    store.atomic(lambda w:w.save_dataset(dataset))
    with pytest.raises(RevisionConflict):
        service.calculate(body.model_copy(update=dict(commit=True,preview_token=result['preview_token'])))

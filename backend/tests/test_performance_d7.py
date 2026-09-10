"""Independent algebraic references and period/service failure boundaries."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
import pytest
from fastapi.testclient import TestClient

from atlas_quant import performance
from atlas_quant.app import create_app
from atlas_quant.book import NativeBook, balance, BookError
from atlas_quant.catalog import RevisionConflict
from atlas_quant.performance import xirr, twr
from atlas_quant.performance_contracts import PerformanceInput, PerformanceReport
from atlas_quant.performance_service import PerformanceService
from atlas_quant.portfolios import PortfolioService
from atlas_quant.store import UnitOfWork
from test_multicurrency_d6 import setup, body, confirm, row, dump, LOCAL, sheet
from test_market_valuation_d6 import invested, market_request, import_market, bind_prices, bind_fx


@pytest.mark.parametrize('terminal,expected', [('1100',.1),('800',-.2),('1000',0),('500',-.5)])
def test_xirr_independent_one_year_identity(terminal, expected):
    result=xirr([('2025-01-01','-1000'),('2026-01-01',terminal)])
    assert result['status']=='complete'
    assert abs(float(result['value'])-expected)<=1e-10
    assert float(result['bracket_width'])<=1e-10
    assert float(result['normalized_residual'])<=1e-10


def test_xirr_irregular_flow_and_leap_year_actual_days():
    result=xirr([('2025-01-01','-1000'),('2025-03-15','-500'),('2026-01-01','1639.6151726494454')])
    assert abs(float(result['value'])-.1)<1e-10
    # 01/01/2024 to 31/12/2024 is exactly 365 days despite a leap year.
    result=xirr([('2024-01-01','-1000'),('2024-12-31','1100')])
    assert abs(float(result['value'])-.1)<1e-10


@pytest.mark.parametrize('flows,reason', [
    ([('2025-01-01','-100'),('2026-01-01','230'),('2027-01-01','-132')], 'unsupported_cashflow_pattern'),
    ([('2025-01-01','100'),('2026-01-01','-110')], 'unsupported_cashflow_pattern'),
    ([('2025-01-01','-1'),('2026-01-01','2000')], 'out_of_domain'),
    ([('2025-01-01','-1'),('2026-01-01','0.0000001')], 'out_of_domain'),
    ([('2025-01-01','100'),('2026-01-01','100')], 'no_investment'),
    ([('2025-01-01','-100'),('2025-01-01','110')], 'no_duration'),
    ([], 'no_investment'),
    ([('2025-01-01','-1000'),('2026-01-01','0')], 'no_positive_recovery'),
])
def test_xirr_never_invents_a_zero_or_selects_an_ambiguous_root(flows,reason):
    result=xirr(flows)
    assert result['value'] is None and result['reasons']==[reason]


def test_group_same_day_before_analyzing_signs():
    result=xirr([('2025-01-01','100'),('2025-01-01','-1100'),('2026-01-01','1100')])
    assert abs(float(result['value'])-.1)<1e-10


def points(values, flows):
    return [dict(date=f'2026-01-0{i+5}', nav_exact=n, flow_eur=f, status='complete',twr_factor=None)
            for i,(n,f) in enumerate(zip(values,flows))]


def test_twr_independent_flow_chain_and_commission():
    result=twr(points(['1000','1200','1320'],['0','100','0']))
    assert Decimal(result['value'])==Decimal('.21')
    result=twr(points(['1000','1098'],['0','100']))
    assert Decimal(result['value'])==Decimal('-.002')


def test_twr_separates_empty_recapitalized_or_missing_intervals():
    for values,flows in [(['100','0','100','110'],['0','-100','100','0']),
                         (['100',None,'100','110'],['0','0','0','0'])]:
        result=twr(points(values,flows))
        assert result['value'] is None and result['status']=='unavailable'
        assert result['segments'][-1]['value']=='0.1'
    assert twr(points(['100','0'],['0','0']))['value']=='-1'
    assert twr(points(['100','1'],['0','200']))['value'] is None


def request(store,p,start='2026-01-05',end='2026-01-06'):
    return PerformanceInput(start_date=start,end_date=end,expected_revision=PortfolioService(store).list()[0]['revision'])


def test_native_usd_period_pnl_excludes_opening_flow_and_uses_both_fx(setup):
    store,_,p,mapping=invested(setup)
    bind_prices(store,p,import_market(store,market_request(mapping))['series'])
    bind_fx(store,p,import_market(store,market_request(mapping,'fx'),'fx')['series'])
    value=PerformanceService(store).calculate(p['id'],request(store,p))['report']
    PerformanceReport.model_validate(value)
    assert value['initial_nav']=='898.20' and value['final_nav']=='986.10'
    assert value['pnl']['display_value']=='87.90'
    assert value['external_net']['value']=='0' and value['costs']==[]
    assert abs(Decimal(value['twr']['value'])-(Decimal('986.1')/Decimal('898.2')-1))<Decimal('1e-25')
    assert value['mwr']['value'] is None and value['mwr']['reasons']==['out_of_domain']


def test_deposit_fee_is_cost_not_a_reduced_external_flow(setup):
    store,books,p,_=setup
    confirm(books,p['id'],body(setup,[row('deposit',gross_amount='1000.00'),
        row('deposit',external_id='second',date='2026-01-06',gross_amount='100.00',fee_amount='2.00')]))
    result=PerformanceService(store).calculate(p['id'],request(store,p))['report']
    assert result['pnl']['value']=='-2' and result['external_net']['value']=='100'
    assert result['costs_eur']['value']=='2' and result['twr']['value']=='-0.002'
    assert len(result['costs'])==1


def test_missing_intermediate_mark_prevents_twr_but_not_endpoint_mwr(setup):
    store,books,p,mapping=invested(setup,'EUR')
    series=market_request(mapping,currency='EUR',days=['2026-01-05','2026-01-20'],values=['100','101'])
    calendar='date,status,close_at\n'+''.join(f'2026-01-{d:02},open,2026-01-{d:02}T20:00:00Z\n' for d in range(5,21))
    series=series.model_copy(update={'evidence':series.evidence.model_copy(update={'calendar_csv':calendar})})
    bind_prices(store,p,import_market(store,series)['series'])
    result=PerformanceService(store).calculate(p['id'],request(store,p,end='2026-01-20'))['report']
    assert result['pnl']['value']=='4' and result['pnl']['status']=='complete'
    assert result['twr']['value'] is None
    assert result['mwr']['value'] is not None and result['mwr']['status']=='complete'
    assert any(p['nav'] is None for p in result['points'])


def test_missing_fx_for_in_period_flow_blocks_pnl_and_mwr(setup):
    store,books,p,mapping=setup
    confirm(books,p['id'],body(setup,[row('deposit',currency='USD',gross_amount='1000.00')]))
    bind_fx(store,p,import_market(store,market_request(mapping,'fx',days=['2026-01-06'],values=['0.9']),'fx')['series'])
    result=PerformanceService(store).calculate(p['id'],request(store,p,start='2026-01-04'))['report']
    assert result['final_nav']=='900.00'
    assert result['pnl']['value'] is None and 'missing_flow_fx' in result['pnl']['reasons']
    assert result['mwr']['value'] is None


def test_saved_period_is_idempotent_and_stays_immutable_when_book_changes(setup):
    store,books,p,_=setup
    service=PerformanceService(store)
    body0=request(store,p)
    preview=service.calculate(p['id'],body0)
    commit=body0.model_copy(update={'commit':True,'preview_token':preview['preview_token']})
    saved=service.calculate(p['id'],commit)
    before=dump(store.path)
    assert service.calculate(p['id'],commit)==saved and dump(store.path)==before
    confirm(books,p['id'],body(setup,[row('deposit',gross_amount='10.00')]))
    old=service.read(p['id'],saved['report']['id'])
    assert old['current'] is False and old['final_nav']=='0.00'
    assert len(service.history(p['id'])['reports'])==1


def test_report_audit_failure_rolls_back_body_and_summary(setup,monkeypatch):
    store,_,p,_=setup
    service=PerformanceService(store)
    body0=request(store,p)
    preview=service.calculate(p['id'],body0)
    before=dump(store.path)
    def fail(*_args,**_kwargs):raise RuntimeError('audit failure')
    monkeypatch.setattr(UnitOfWork,'audit',fail)
    with pytest.raises(RuntimeError):
        service.calculate(p['id'],body0.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))
    assert dump(store.path)==before


def test_report_rechecks_context_after_calculation(setup,monkeypatch):
    store,books,p,_=setup
    service=PerformanceService(store)
    body0=request(store,p)
    preview=service.calculate(p['id'],body0)
    original=performance.calculate
    def change(*args):
        value=original(*args)
        confirm(books,p['id'],body(setup,[row('deposit',gross_amount='1.00')]))
        return value
    monkeypatch.setattr(performance,'calculate',change)
    with pytest.raises(RevisionConflict):
        service.calculate(p['id'],body0.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))
    assert service.history(p['id'])['reports']==[]


def test_two_report_confirmations_publish_one_immutable_result(setup,monkeypatch):
    store,_,p,_=setup
    service=PerformanceService(store)
    body0=request(store,p)
    preview=service.calculate(p['id'],body0)
    commit=body0.model_copy(update={'commit':True,'preview_token':preview['preview_token']})
    gate=Barrier(2)
    original=performance.calculate
    def wait(*args):
        value=original(*args)
        gate.wait(timeout=5)
        return value
    monkeypatch.setattr(performance,'calculate',wait)
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:service.calculate(p['id'],commit),range(2)))
    assert results[0]==results[1]
    assert len(service.history(p['id'])['reports'])==1


def test_period_http_contract_guard_and_bounds(setup):
    store,_,p,_=setup
    with TestClient(create_app(store.path.parent,run_worker=False)) as client:
        path=f'/api/v2/portfolios/{p["id"]}/performance'
        payload=request(store,p).model_dump()
        assert client.post(path,json=payload).status_code==403
        result=client.post(path,json=payload,headers=LOCAL)
        assert result.status_code==200,result.text
        PerformanceReport.model_validate(result.json()['report'])
        assert client.post(path,json={**payload,'end_date':payload['start_date']},headers=LOCAL).status_code==422
        assert client.post(path,json={**payload,'start_date':'2000-01-01'},headers=LOCAL).status_code==422
        assert client.get(path+'/unknown').status_code==404


def test_heavy_read_limit_leaves_control_available_and_releases_slots(setup):
    from atlas_quant.computation import _SLOTS
    store,_,p,_=setup
    with TestClient(create_app(store.path.parent,run_worker=False)) as client:
        _SLOTS.acquire()
        _SLOTS.acquire()
        try:
            response=client.post(f'/api/v2/portfolios/{p["id"]}/performance',json=request(store,p).model_dump(),headers=LOCAL)
            assert response.status_code==503
            assert client.post('/api/settings',json={'kill_switch':True},headers=LOCAL).status_code==200
        finally:
            _SLOTS.release()
            _SLOTS.release()
        response=client.post(f'/api/v2/portfolios/{p["id"]}/performance',json=request(store,p).model_dump(),headers=LOCAL)
        assert response.status_code==200


def test_incremental_book_reuses_exact_reducer_and_old_snapshots_do_not_mutate(setup):
    store,books,p,_=setup
    confirm(books,p['id'],body(setup,[row('deposit',gross_amount='1000.00'),
        row('buy',day_sequence='2',listing_ref='EUR',quantity='3',unit_price='100',gross_amount='300.00'),
        row('sell',date='2026-01-06',listing_ref='EUR',quantity='1',unit_price='110',gross_amount='110.00',fee_amount='1.00')]))
    entries=store.read(lambda w:w.portfolio_events(w.portfolio_record(p['id'])))
    cursor=NativeBook()
    snapshots=[]
    for item in sorted(entries,key=lambda e:(e['date'],e['day_sequence'])):
        cursor.apply(item)
        snapshots.append(cursor.snapshot(item['date']))
    assert snapshots[0]['balances'][0]['cash']=='1000.00'
    assert snapshots[-1]==balance(entries,'2026-01-06',multicurrency=True)
    assert snapshots[-1]['balances'][0]['realized_pnl']=='9'


def corporate_fixture(setup, kind, gross='0.50'):
    from atlas_quant.corporate import EVENT_COLUMNS
    from atlas_quant.corporate_contracts import CorporateInput
    from atlas_quant.corporate_service import CorporateService
    store,_,_,mapping=setup
    service=CorporateService(store,multicurrency=True)
    event=dict(external_id='event',event_type=kind,listing_ref='EUR',effective_date='2026-01-06',currency='EUR',
        available_at='2026-01-06T10:00:00Z',source_reference='Caso numérico sintético')
    event.update(dict(gross_per_unit=gross,payment_date='2026-01-06') if kind=='dividend' else dict(ratio_numerator='2',ratio_denominator='1'))
    body0=CorporateInput(expected_revision=0,format_id='atlas-corporate-events-v1',source='Fixture D7',mapping=mapping,
        verified=True,evidence='Caso sintético acreditado para esta prueba',csv=sheet(EVENT_COLUMNS,[event]))
    preview=service.import_events(body0)
    event=service.import_events(body0.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))['events'][0]
    return service,event


def test_split_does_not_create_artificial_period_profit(setup):
    from atlas_quant.book import MOVEMENT_COLUMNS
    from atlas_quant.book_contracts import CorporateReview
    from atlas_quant.corporate_contracts import CorporateApplicationInput
    store,books,p,mapping=setup
    confirm(books,p['id'],body(setup,[row('deposit',gross_amount='1000.00'),
        row('buy',day_sequence='2',listing_ref='EUR',quantity='10',unit_price='100',gross_amount='1000.00')]))
    bind_prices(store,p,import_market(store,market_request(mapping,currency='EUR',values=['100','50']))['series'])
    corporate,event=corporate_fixture(setup,'split')
    movement=row('split',date='2026-01-06',listing_ref='ASSET',ratio_numerator='2',ratio_denominator='1',corporate_event_ref='EVENT')
    body0=CorporateApplicationInput(expected_revision=request(store,p).expected_revision,event_id=event['id'],source='Fixture D6',source_account='DEMO-D6',
        review=CorporateReview(event_revision=1,day_sequence=1,evidence='Split sintético exacto'),csv=sheet(MOVEMENT_COLUMNS,[movement]))
    confirm(corporate,p['id'],body0,'apply')
    result=PerformanceService(store).calculate(p['id'],request(store,p))['report']
    assert result['initial_nav']==result['final_nav']=='1000.00'
    assert result['pnl']['value']==result['twr']['value']=='0'
    assert abs(float(result['mwr']['value']))<=1e-10


def test_dividend_receivable_then_payment_preserves_gain_and_explains_tax(setup):
    from atlas_quant.book import MOVEMENT_COLUMNS
    from atlas_quant.book_contracts import CorporateReview
    from atlas_quant.corporate_contracts import CorporateApplicationInput
    store,books,p,mapping=setup
    confirm(books,p['id'],body(setup,[row('deposit',gross_amount='1000.00'),
        row('buy',day_sequence='2',listing_ref='EUR',quantity='100',unit_price='10',gross_amount='1000.00')]))
    bind_prices(store,p,import_market(store,market_request(mapping,currency='EUR',values=['10','10']))['series'])
    corporate,event=corporate_fixture(setup,'dividend')
    body0=CorporateApplicationInput(expected_revision=request(store,p).expected_revision,event_id=event['id'],source='Fixture D6',source_account='DEMO-D6',
        review=CorporateReview(event_revision=1,day_sequence=1,evidence='100 títulos acreditados sintéticos',eligible_quantity='100'))
    confirm(corporate,p['id'],body0,'apply')
    pending=PerformanceService(store).calculate(p['id'],request(store,p))['report']
    assert pending['pnl']['value']=='50'
    movement=row('dividend_payment',date='2026-01-06',listing_ref='ASSET',gross_amount='50.00',fee_amount='0.50',tax_amount='9.50',corporate_event_ref='EVENT')
    confirm(corporate,p['id'],body0.model_copy(update={'expected_revision':request(store,p).expected_revision,'csv':sheet(MOVEMENT_COLUMNS,[movement])}),'apply')
    paid=PerformanceService(store).calculate(p['id'],request(store,p))['report']
    assert paid['pnl']['value']=='40' and paid['final_nav']=='1040.00'
    assert paid['external_net']['value']=='0' and paid['costs_eur']['value']=='10'


def test_unaccredited_dividend_blocks_return_even_before_future_payment(setup):
    store,books,p,mapping=invested(setup,'EUR')
    confirm(books,p['id'],body(setup,[row('dividend_payment',date='2026-01-07',listing_ref='EUR',gross_amount='10.00')],
        unaccredited_payments={'dividend_payment':'Cobro sintético sin exfecha acreditada'}))
    bind_prices(store,p,import_market(store,market_request(mapping,currency='EUR'))['series'])
    value=PerformanceService(store).calculate(p['id'],request(store,p))['report']
    assert value['final_nav']=='1038.00'
    assert value['pnl']['value'] is None and value['pnl']['reasons']==['unlinked_dividend_history']
    assert value['mwr']['value'] is None and value['twr']['value'] is None
    assert all(p['twr_factor'] is None for p in value['points'])


def test_solver_reports_failure_when_requested_precision_is_unattainable(monkeypatch):
    monkeypatch.setattr(performance,'TOLERANCE',1e-100)
    value=xirr([('2025-01-01','-1000'),('2026-01-01','1100')])
    assert value['value'] is None and value['reasons']==['no_convergence']


def test_provisional_marks_produce_qualified_rates(setup):
    store,_,p,mapping=invested(setup,'EUR')
    bind_prices(store,p,import_market(store,market_request(mapping,currency='EUR',values=['100','100.01'],verified=False))['series'])
    value=PerformanceService(store).calculate(p['id'],request(store,p))['report']
    assert value['pnl']['status']==value['twr']['status']==value['mwr']['status']=='provisional'
    assert all(value[k]['value'] is not None for k in ('pnl','twr','mwr'))

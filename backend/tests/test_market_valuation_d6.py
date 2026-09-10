"""D6.3/4 economic examples, temporal boundaries and transactional failures."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3

import pytest
from fastapi.testclient import TestClient
from atlas_quant.app import create_app
from atlas_quant.market_contracts import MarketImport, FxBindingInput
from atlas_quant.market_service import MarketService, PRICE_COLUMNS, FX_COLUMNS
from atlas_quant.quality import EvidenceInput
from atlas_quant.portfolios import PortfolioService
from atlas_quant.catalog import RevisionConflict
from atlas_quant.valuation import MarkSeries
from atlas_quant.valuation_service import ValuationService
from atlas_quant.valuation_contracts import ValuationInput, ValuationCut
from atlas_quant.store import UnitOfWork
from atlas_quant.book import MOVEMENT_COLUMNS
from atlas_quant.corporate import EVENT_COLUMNS
from atlas_quant.corporate_contracts import CorporateInput, CorporateApplicationInput
from atlas_quant.corporate_service import CorporateService
from atlas_quant.book_contracts import CorporateReview
from atlas_quant.valuation import Valuator
from test_multicurrency_d6 import setup, body, confirm, row, sheet, dump, LOCAL


def market_request(mapping, kind='prices', currency='USD', days=None, values=None, verified=True):
    days = days or ['2026-01-05', '2026-01-06']
    values = values or (['100', '110'] if kind == 'prices' else ['0.9', '0.95'])
    bars = [dict(date=d, **(dict(listing_ref='ASSET', open=v, high=v, low=v, close=v, volume='10', currency=currency)
                if kind == 'prices' else dict(from_currency='USD', to_currency='EUR', rate=v)), available_at=d+'T20:01:00Z') for d, v in zip(days, values)]
    calendar = 'date,status,close_at\n' + ''.join(d+',open,'+d+'T20:00:00Z\n' for d in days)
    evidence = EvidenceInput(symbol='ASSET', calendar_name='Fixture', market='TEST', calendar_source='Calendario sintético',
                            calendar_verified=verified, calendar_csv=calendar if verified else '', price_basis='raw', basis_verified=True, basis_source='Precios brutos ficticios')
    return MarketImport(name='Fixture '+kind, source='Datos ficticios D6', listing_id=mapping[currency] if kind == 'prices' else None,
                        csv=sheet(PRICE_COLUMNS if kind == 'prices' else FX_COLUMNS, bars), evidence=evidence)


def import_market(store, request, kind='prices'):
    service = MarketService(store)
    preview = service.import_series(kind, request)
    return service.import_series(kind, request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))


def bind_prices(store, p, series):
    binding = dict(listing_id=series['listing_id'], dataset_id=series['id'], dataset_version=series['version'], symbol=series['symbol'])
    service = PortfolioService(store)
    preview = service.bind(p['id'], [binding])
    service.bind(p['id'], [binding], True, preview['preview_token'])


def bind_fx(store, p, series):
    service = MarketService(store)
    revision = PortfolioService(store).list()[0]['revision']
    request = FxBindingInput(expected_revision=revision, series_id=series['id'], series_version=series['version'])
    preview = service.bind_fx(p['id'], request)
    return service.bind_fx(p['id'], request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))


def nav_request(store, p, day='2026-01-06'):
    return ValuationInput(as_of_date=day, expected_revision=PortfolioService(store).list()[0]['revision'])


def invested(setup, currency='USD'):
    store, service, p, mapping = setup
    request = body(setup, [row('deposit', gross_amount='1000.00', currency=currency),
        row('buy', listing_ref=currency, quantity='4', unit_price='100', gross_amount='400.00', fee_amount='2.00', currency=currency, day_sequence='2')])
    confirm(service, p['id'], request)
    return setup


def test_exact_usd_nav_with_native_cash_price_and_historical_flow(setup):
    store, _, p, mapping = invested(setup)
    prices = import_market(store, market_request(mapping))['series']
    fx = import_market(store, market_request(mapping, 'fx'), 'fx')['series']
    bind_prices(store, p, prices)
    bind_fx(store, p, fx)
    service, request = ValuationService(store), nav_request(store, p)
    preview = service.calculate(p['id'], request)
    cut = preview['cut']
    ValuationCut.model_validate(cut)
    assert cut['status'] == 'complete'
    # 598 USD cash + 4*110 USD stock, both at .95 EUR/USD.
    assert cut['value'] == '986.10'
    assert cut['flows'][0]['eur_amount'] == '900'
    assert cut['historical_known'] is True
    saved = service.calculate(p['id'], request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    before = dump(store.path)
    again = service.calculate(p['id'], request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert saved == again
    assert dump(store.path) == before
    assert service.read(p['id'], saved['cut']['id'])['saved']


def test_usd_missing_fx_is_not_zero_and_does_not_corrupt_eur_legacy(setup):
    store, _, p, mapping = invested(setup)
    bind_prices(store, p, import_market(store, market_request(mapping))['series'])
    cut = ValuationService(store).calculate(p['id'], nav_request(store, p))['cut']
    assert cut['status'] == 'incomplete' and cut['value'] is None
    assert 'missing_fx' in cut['reasons']
    assert cut['balance']['positions'][0]['quantity'] == '4'
    assert cut['flows'][0]['eur_amount'] is None


def test_old_flow_without_fx_does_not_invalidate_current_nav(setup):
    store, _, p, mapping = invested(setup)
    bind_prices(store, p, import_market(store, market_request(mapping))['series'])
    bind_fx(store, p, import_market(store, market_request(mapping, 'fx', days=['2026-01-06'], values=['0.95']), 'fx')['series'])
    cut = ValuationService(store).calculate(p['id'], nav_request(store, p))['cut']
    assert cut['status'] == 'complete' and cut['value'] == '986.10'
    assert cut['flows'][0]['status'] == 'incomplete'


@pytest.mark.parametrize('days,status,reason', [(7, 'provisional', 'calendar_unknown'), (8, 'incomplete', 'stale_mark')])
def test_seven_eight_day_boundary(setup, days, status, reason):
    store, _, _, mapping = setup
    result = import_market(store, market_request(mapping, 'fx', days=['2026-01-05'], values=['0.9'], verified=False), 'fx')
    data = store.atomic(lambda w: w.market_version('fx', result['series']['id'], 1))
    mark = MarkSeries(data, 'USD_EUR', 'fx').select('2026-01-'+str(5+days), '2026-02-01T00:00:00Z')
    assert mark['status'] == status and reason in mark['reasons']
    assert (mark['value'] is None) == (status == 'incomplete')


def test_verified_closed_days_and_unknown_decision_availability(setup):
    store, _, _, mapping = setup
    request = market_request(mapping, 'fx', days=['2026-01-05'], values=['0.9'])
    request = request.model_copy(update={'csv': request.csv.replace('2026-01-05T20:01:00Z', ''), 'evidence': request.evidence.model_copy(update={
        'calendar_csv': request.evidence.calendar_csv + '\n' + ''.join(f'2026-01-{d:02},closed,\n' for d in range(6, 15))})})
    series = import_market(store, request, 'fx')['series']
    data = store.atomic(lambda w: w.market_version('fx', series['id'], 1))
    mark = MarkSeries(data, 'USD_EUR', 'fx').select('2026-01-14', '2026-01-14T23:59:59Z')
    assert mark['status'] == 'complete' and mark['age_days'] == 9
    assert not mark['historical_known'] and mark['historical_reasons'] == ['availability_unknown']
    assert MarkSeries(data, 'USD_EUR', 'fx').select('2026-01-04', '2026-01-04T23:59:59Z')['value'] is None


def test_idempotent_import_reviewed_revision_and_frozen_cut(setup):
    store, _, p, mapping = invested(setup)
    request = market_request(mapping)
    series = import_market(store, request)['series']
    request = request.model_copy(update={'series_id': series['id'], 'expected_version': 1})
    before = dump(store.path)
    assert import_market(store, request)['series']['version'] == 1
    assert dump(store.path) == before
    bind_prices(store, p, series)
    bind_fx(store, p, import_market(store, market_request(mapping, 'fx'), 'fx')['series'])
    nav = ValuationService(store)
    inp = nav_request(store, p)
    preview = nav.calculate(p['id'], inp)
    saved = nav.calculate(p['id'], inp.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))['cut']
    revised = request.model_copy(update={'csv': request.csv.replace('110', '120')})
    with pytest.raises(ValueError, match='revisión explícita'):
        import_market(store, revised)
    updated = import_market(store, revised.model_copy(update={'revise_history': True, 'reason': 'Corrección ficticia'}))
    assert updated['changed'] == 1 and updated['series']['version'] == 2
    assert updated['affected_portfolios'] == [p['id']]
    old = nav.read(p['id'], saved['id'])
    assert old['value'] == '986.10' and old['current'] is False
    assert MarketService(store).read('prices', series['id'], 1)['observations'][1]['close'] == '110'


@pytest.mark.parametrize('change', [dict(csv='date,from_currency,to_currency,rate,available_at\n2026-01-05,EUR,USD,1.1,\n'),
    dict(csv='date,from_currency,to_currency,rate,available_at\n2026-01-05,USD,EUR,NaN,\n'),
    dict(csv='date,from_currency,to_currency,rate,available_at\n2099-01-05,USD,EUR,1.1,\n'),
    dict(csv='date,from_currency,to_currency,rate,available_at\n2026-01-05,USD,EUR,0.1234567890123456789,\n')])
def test_invalid_fx_is_atomic(setup, change):
    store, _, _, mapping = setup
    before = dump(store.path)
    with pytest.raises(ValueError):
        import_market(store, market_request(mapping, 'fx').model_copy(update=change), 'fx')
    assert dump(store.path) == before


def test_price_identity_and_basis_are_not_guessed(setup):
    store, _, p, mapping = invested(setup)
    request = market_request(mapping)
    with pytest.raises(ValueError, match='moneda'):
        import_market(store, request.model_copy(update={'csv': request.csv.replace('USD', 'EUR')}))
    request = request.model_copy(update={'evidence': None})
    prices = import_market(store, request)['series']
    bind_prices(store, p, prices)
    bind_fx(store, p, import_market(store, market_request(mapping, 'fx'), 'fx')['series'])
    cut = ValuationService(store).calculate(p['id'], nav_request(store, p))['cut']
    assert cut['value'] is None and 'price_basis_incompatible' in cut['reasons']


def test_failed_market_audit_rolls_back_version(setup, monkeypatch):
    store, _, _, mapping = setup
    request = market_request(mapping, 'fx')
    service = MarketService(store)
    preview = service.import_series('fx', request)
    before = dump(store.path)
    original = UnitOfWork.audit
    def fail(self, event, *args, **kwargs):
        if event == 'market.version_imported':
            raise RuntimeError('simulated failure')
        return original(self, event, *args, **kwargs)
    monkeypatch.setattr(UnitOfWork, 'audit', fail)
    with pytest.raises(RuntimeError):
        service.import_series('fx', request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert dump(store.path) == before


def test_concurrent_confirmations_have_one_winner(setup, monkeypatch):
    store, _, _, mapping = setup
    service, request = MarketService(store), market_request(mapping, 'fx')
    preview = service.import_series('fx', request)
    request = request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']})
    barrier = Barrier(2)
    # Synchronize outside the transaction, after the first coherent snapshot.
    original_atomic = store.atomic
    from threading import local
    state = local()
    def atomic(callback):
        value = original_atomic(callback)
        if not getattr(state, 'read', False):
            state.read = True
            barrier.wait(timeout=5)
        return value
    monkeypatch.setattr(store, 'atomic', atomic)
    def run():
        try:
            service.import_series('fx', request)
            return 'saved'
        except RevisionConflict:
            return 'conflict'
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _: run(), range(2))) == ['conflict', 'saved']


def test_http_contracts_and_old_state_exclude_native_datasets(setup):
    store, _, p, mapping = setup
    with TestClient(create_app(store.path.parent, run_worker=False)) as client:
        request = market_request(mapping, 'fx').model_dump(mode='json')
        response = client.post('/api/v2/market/fx/imports', json=request, headers=LOCAL)
        assert response.status_code == 200, response.text
        request.update(commit=True, preview_token=response.json()['preview_token'])
        result = client.post('/api/v2/market/fx/imports', json=request, headers=LOCAL)
        assert result.status_code == 200, result.text
        catalog = client.get('/api/v2/market')
        assert catalog.status_code == 200 and len(catalog.json()['series']) == 1
        assert client.get('/api/state').status_code == 200
        response = client.post(f'/api/v2/portfolios/{p["id"]}/valuations', json=nav_request(store, p).model_dump(), headers=LOCAL)
        assert response.status_code == 200, response.text
        assert response.json()['cut']['value'] == '0.00'


def test_zero_exposure_requires_no_fx_even_after_usd_history(setup):
    store, service, p, _ = setup
    confirm(service, p['id'], body(setup, [row('deposit', currency='USD', gross_amount='1.00'),
        row('withdrawal', day_sequence='2', currency='USD', gross_amount='1.00')]))
    result = ValuationService(store).calculate(p['id'], nav_request(store, p))['cut']
    assert result['status'] == 'complete' and result['value'] == '0.00'
    assert all(f['eur_amount'] is None for f in result['flows'])


def test_total_rounds_once_not_each_component(setup):
    store, service, p, mapping = setup
    confirm(service, p['id'], body(setup, [row('deposit', gross_amount='0.01'),
        row('deposit', external_id='usd', day_sequence='2', currency='USD', gross_amount='0.01')]))
    bind_fx(store, p, import_market(store, market_request(mapping, 'fx', values=['0.5', '0.5']), 'fx')['series'])
    result = ValuationService(store).calculate(p['id'], nav_request(store, p))['cut']
    assert result['exact_value'] == '0.015' and result['value'] == '0.02'
    assert result['rounding_difference'] == '0.01'


def test_saved_nav_rechecks_concurrent_book_changes(setup, monkeypatch):
    store, books, p, _ = setup
    service, request = ValuationService(store), nav_request(store, p)
    preview = service.calculate(p['id'], request)
    original = Valuator.cut
    def change(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        confirm(books, p['id'], body(setup, [row('deposit', gross_amount='1.00')]))
        return result
    monkeypatch.setattr(Valuator, 'cut', change)
    with pytest.raises(RevisionConflict):
        service.calculate(p['id'], request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert store.atomic(lambda w: w.valuations(p['id'])) == []
    assert books.read(p['id'])['balance']['balances'][0]['cash'] == '1.00'


def test_native_dividend_is_counted_once_and_paid_fees_reduce_nav(setup):
    store, books, p, mapping = setup
    confirm(books, p['id'], body(setup, [row('deposit', currency='USD', gross_amount='1100.00'),
        row('buy', day_sequence='2', currency='USD', listing_ref='USD', quantity='100', unit_price='10', gross_amount='1000.00')]))
    prices = market_request(mapping, days=['2026-01-05','2026-01-06'], values=['10','10'])
    bind_prices(store,p,import_market(store,prices)['series'])
    bind_fx(store,p,import_market(store,market_request(mapping,'fx',values=['0.9','0.9']),'fx')['series'])
    corp=CorporateService(store,multicurrency=True)
    events=CorporateInput(expected_revision=0,format_id='atlas-corporate-events-v1',source='Fixture D6',mapping=mapping,verified=True,evidence='Derecho ficticio acreditado',
        csv=sheet(EVENT_COLUMNS,[dict(external_id='right',event_type='dividend',listing_ref='USD',effective_date='2026-01-06',payment_date='2026-01-06',
            gross_per_unit='0.50',currency='USD',source_reference='Fixture',available_at='2026-01-06T10:00:00Z')]))
    event=corp.import_events(events)
    event=corp.import_events(events.model_copy(update={'commit':True,'preview_token':event['preview_token']}))['events'][0]
    nav=ValuationService(store)
    blocked=nav.calculate(p['id'],nav_request(store,p))['cut']
    assert blocked['value'] is None and 'corporate_action_unresolved' in blocked['reasons']
    review=CorporateReview(event_revision=1,day_sequence=10,evidence='100 títulos sintéticos acreditados',eligible_quantity='100')
    request=CorporateApplicationInput(expected_revision=nav_request(store,p).expected_revision,event_id=event['id'],source='Fixture D6',source_account='DEMO-D6',review=review)
    confirm(corp,p['id'],request,'apply')
    right=nav.calculate(p['id'],nav_request(store,p))['cut']
    assert right['status']=='complete' and right['value']=='1035.00'
    assert next(c for c in right['components'] if c['kind']=='receivable')['native_value']=='50'
    payment=sheet(MOVEMENT_COLUMNS,[row('dividend_payment',date='2026-01-06',day_sequence='20',listing_ref='ASSET',currency='USD',gross_amount='50.00',fee_amount='0.50',tax_amount='9.50',corporate_event_ref='EVENT')])
    confirm(corp,p['id'],request.model_copy(update={'expected_revision':nav_request(store,p).expected_revision,'csv':payment}),'apply')
    paid=nav.calculate(p['id'],nav_request(store,p))['cut']
    assert paid['value']=='1026.00' and paid['status']=='complete'
    assert not any(c['kind']=='receivable' for c in paid['components'])


def test_old_price_route_rejects_native_contract_cleanly(setup):
    store,_,_,mapping=setup
    series=import_market(store,market_request(mapping))['series']
    with TestClient(create_app(store.path.parent,run_worker=False)) as client:
        response=client.get(f'/api/datasets/{series["id"]}/prices?version=1&symbol=ASSET')
        assert response.status_code==422, response.text


def test_read_snapshot_is_coherent_during_a_writer_and_cannot_write(setup):
    store, _, _, _ = setup
    store.put('fixture', {'id': 'snapshot', 'value': 1})
    def snapshot(work):
        assert work.get('fixture', 'snapshot')['value'] == 1
        with ThreadPoolExecutor(1) as pool:
            pool.submit(store.put, 'fixture', {'id': 'snapshot', 'value': 2}).result(timeout=2)
        assert work.get('fixture', 'snapshot')['value'] == 1
        with pytest.raises(sqlite3.OperationalError, match='readonly'):
            work.put('fixture', {'id': 'illegal'})
    store.read(snapshot)
    assert store.get('fixture', 'snapshot')['value'] == 2
    assert store.get('fixture', 'illegal') is None


def test_native_identity_cannot_be_rewritten_by_legacy_importer(setup):
    store, _, _, mapping = setup
    series = import_market(store, market_request(mapping))['series']
    before = dump(store.path)
    with pytest.raises(ValueError, match='nativa'):
        store.save_dataset({'id': series['id']})
    assert dump(store.path) == before


@pytest.mark.parametrize('effective', [None, '2026-01-05'])
def test_unknown_or_same_day_corporate_event_requires_review(setup, effective):
    store, _, p, mapping = invested(setup)
    bind_prices(store, p, import_market(store, market_request(mapping))['series'])
    bind_fx(store, p, import_market(store, market_request(mapping, 'fx'), 'fx')['series'])
    context = store.read(lambda w: ValuationService.context(w, p['id']))
    context['corporate']['events'] = [dict(id='unreviewed', listing_id=mapping['USD'],
        effective_date=effective, cancelled=False)]
    result = Valuator(context).cut('2026-01-06')
    assert result['value'] is None and 'corporate_action_unresolved' in result['reasons']

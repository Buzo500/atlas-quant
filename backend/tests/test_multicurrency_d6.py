"""Independent native-currency examples and real atomic/HTTP boundaries, no FX marks."""
import io
import csv
import json
import sqlite3
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from atlas_quant.app import create_app
from atlas_quant.book import POLICY, MOVEMENT_COLUMNS, STATEMENT_COLUMNS, BookError
from atlas_quant.book_service import BookService
from atlas_quant.book_contracts import ImportInput, ReconciliationInput, CorrectionInput, CorporateReview
from atlas_quant.catalog import CatalogService, RevisionConflict
from atlas_quant.corporate import EVENT_COLUMNS
from atlas_quant.corporate_contracts import CorporateInput, CorporateApplicationInput
from atlas_quant.corporate_service import CorporateService
from atlas_quant.portfolios import PortfolioService
from atlas_quant.store import Store, UnitOfWork
from atlas_quant.valuation_store import DDL
from atlas_quant.backup import create_backup, validate_backup

LOCAL = {'x-atlas-client': 'local-v1'}
REFERENCES = json.loads((Path(__file__).parents[2] / 'docs/fixtures/v0_4_d6_referencias.json').read_text(encoding='utf-8'))


def expected(case, name):
    return next(step['expected'] for c in REFERENCES['numeric_cases'] if c['id'] == case for step in c['calculations'] if step['name'] == name)


def sheet(columns, values):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows(values)
    return stream.getvalue()


def row(kind, **changes):
    currency = changes.get('currency', 'EUR')
    result = dict(external_id=kind, date='2026-01-05', day_sequence='1', kind=kind,
                  currency=currency, fee_currency=currency, fee_amount='0.00', tax_currency=currency, tax_amount='0.00')
    if kind == 'fx_exchange':
        result.update(tax_amount='', tax_currency='')
    if kind == 'split':
        result.update(fee_amount='', fee_currency='', tax_amount='', tax_currency='')
    return {**result, **changes}


@pytest.fixture
def setup(tmp_path):
    store = Store(tmp_path / 'atlas.sqlite3')
    cat = CatalogService(store)
    c = cat.add('instrument', dict(expected_revision=0, name='Activo ficticio D6', source='Fixture D6'))
    mapping = {}
    for currency in ('EUR', 'USD'):
        c = cat.add('listing', dict(expected_revision=c['revision'], instrument_id=c['instruments'][0]['id'], currency=currency))
        mapping[currency] = next(i['id'] for i in c['listings'] if i['currency'] == currency)
    p = PortfolioService(store).create('D6 sintética', POLICY)
    return store, BookService(store, multicurrency=True), p, mapping


def body(setup, rows, **changes):
    store, _, p, mapping = setup
    return ImportInput(**dict(format_id='atlas-ledger-v2', expected_revision=PortfolioService(store).read(p['id'])['portfolio']['revision'],
        source='Fixture D6', source_account='DEMO-D6', as_of_date='2026-03-01', mapping=mapping,
        csv=sheet(MOVEMENT_COLUMNS, rows), **changes))


def confirm(service, ident, request, method='import_movements'):
    call = getattr(service, method)
    preview = call(ident, request)
    return call(ident, request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))


def cash(result, currency):
    return next(b for b in result['balance']['balances'] if b['currency'] == currency)


def dump(path):
    with closing(sqlite3.connect(path)) as db:
        tables = [r[0] for r in db.execute("select name from sqlite_master where type='table'")]
        return {t: db.execute(f'SELECT * FROM "{t}" ORDER BY rowid').fetchall() for t in tables}


def exchange_rows(fee_currency='EUR'):
    return [row('deposit', gross_amount='1000.00'), row('fx_exchange', day_sequence='2', gross_amount='400.00', fx_to_amount='440.00', fx_to_currency='USD', fee_amount='2.00', fee_currency=fee_currency)]


@pytest.mark.parametrize('fee_currency,oracle', [('EUR', 'D6-N02'), ('USD', 'D6-N03')])
def test_exchange_uses_actual_legs_fee_currency_and_no_external_flow(setup, fee_currency, oracle):
    store, service, p, _ = setup
    request = body(setup, exchange_rows(fee_currency))
    result = confirm(service, p['id'], request)
    from decimal import Decimal
    assert Decimal(cash(result, 'EUR')['cash']) == Decimal(expected(oracle, 'cash_eur'))
    assert Decimal(cash(result, 'USD')['cash']) == Decimal(expected(oracle, 'cash_usd'))
    assert cash(result, 'EUR')['net_contributions'] == '1000.00'
    assert cash(result, 'USD')['net_contributions'] == '0.00'
    assert 'cash' not in result['balance']
    again = confirm(service, p['id'], body(setup, exchange_rows(fee_currency)))
    assert again['added'] == 0 and again['duplicates'] == 2
    assert again['balance'] == result['balance']
    with pytest.raises(BookError, match='multidivisa'):
        BookService(store).read(p['id'])


def test_usd_buy_partial_sale_cost_residue_and_reverse_exchange(setup):
    _, service, p, mapping = setup
    rows = exchange_rows() + [row('buy', day_sequence='3', currency='USD', listing_ref='USD', quantity='3', unit_price='100', gross_amount='300.00', fee_amount='1.00')]
    bought = confirm(service, p['id'], body(setup, rows))
    assert cash(bought, 'USD')['cash'] == '139.00'
    assert bought['balance']['positions'] == [dict(listing_id=mapping['USD'], currency='USD', quantity='3', cost_basis='301')]
    sold = confirm(service, p['id'], body(setup, [row('sell', day_sequence='4', currency='USD', listing_ref='USD', quantity='2', unit_price='120', gross_amount='240.00', fee_amount='1.00')]))
    assert cash(sold, 'USD')['cash'] == '378.00'
    assert cash(sold, 'USD')['realized_pnl'] == expected('D6-N05', 'realized_usd')
    assert sold['balance']['positions'][0]['cost_basis'] == expected('D6-N05', 'remaining_basis_usd')
    closed = confirm(service, p['id'], body(setup, [row('sell', external_id='sell-final', day_sequence='5', currency='USD', listing_ref='USD', quantity='1', unit_price='120', gross_amount='120.00', fee_amount='1.00')]))
    assert closed['balance']['positions'] == []
    assert cash(closed, 'USD')['cash'] == '497.00'
    assert cash(closed, 'USD')['realized_pnl'] == '57'
    reversed_ = confirm(service, p['id'], body(setup, [row('fx_exchange', external_id='reverse', day_sequence='6', currency='USD', gross_amount='110.00', fx_to_amount='100.00', fx_to_currency='EUR', fee_amount='1.00', fee_currency='EUR')]))
    assert cash(reversed_, 'USD')['cash'] == '387.00'
    assert cash(reversed_, 'EUR')['cash'] == '697.00'
    assert cash(reversed_, 'EUR')['net_contributions'] == '1000.00'


@pytest.mark.parametrize('bad', [
    row('buy', day_sequence='2', currency='USD', listing_ref='USD', quantity='1', unit_price='100', gross_amount='100.00'),
    row('fx_exchange', day_sequence='2', gross_amount='1000.00', fx_to_amount='1100.00', fx_to_currency='USD', fee_amount='0.01'),
    row('fx_exchange', day_sequence='2', gross_amount='500.00', fx_to_amount='1.00', fx_to_currency='USD', fee_amount='1.01', fee_currency='USD'),
])
def test_insufficient_currency_rejects_whole_batch_and_success_audit(setup, bad):
    store, service, p, _ = setup
    before = dump(store.path)
    with pytest.raises(BookError) as error:
        service.import_movements(p['id'], body(setup, [row('deposit', gross_amount='1000.00'), bad]))
    assert error.value.code == 'insufficient_cash'
    assert dump(store.path) == before


@pytest.mark.parametrize('change,code', [
    ({'fx_to_currency': 'EUR'}, 'unsupported_currency'), ({'currency': 'GBP'}, 'unsupported_currency'),
    ({'gross_amount': '1e2'}, 'invalid_decimal'), ({'fx_to_amount': 'NaN'}, 'invalid_decimal'),
    ({'fee_amount': '0.001'}, 'invalid_decimal'), ({'tax_amount': '0.00'}, 'incompatible_field'),
    ({'quantity': '1'}, 'incompatible_field'), ({'fx_to_amount': '0'}, 'invalid_decimal'),
    ({'fx_to_amount': '1000000000000000001'}, 'numeric_range'),
])
def test_exchange_rejects_ambiguous_or_invalid_fields(setup, change, code):
    store, service, p, _ = setup
    rows = exchange_rows(); rows[1].update(change)
    before = dump(store.path)
    with pytest.raises(BookError) as error:
        service.import_movements(p['id'], body(setup, rows))
    assert error.value.code == code
    assert dump(store.path) == before


def test_listing_currency_must_match_trade_and_statement(setup):
    store, service, p, mapping = setup
    with pytest.raises(BookError) as error:
        service.import_movements(p['id'], body(setup, [row('deposit', gross_amount='1000.00'), row('buy', day_sequence='2', listing_ref='USD', quantity='1', unit_price='1', gross_amount='1.00')]))
    assert error.value.code == 'currency_mismatch'
    request = ReconciliationInput(expected_revision=1, format_id='atlas-statement-v2', source='Fixture D6', source_account='DEMO-D6', as_of_date='2026-03-01', mapping=mapping, complete_statement=True,
        csv=sheet(STATEMENT_COLUMNS, [dict(as_of_date='2026-03-01', record_type='cash', currency='EUR', amount='0.00'), dict(as_of_date='2026-03-01', record_type='position', listing_ref='USD', currency='EUR', quantity='1')]))
    with pytest.raises(BookError) as error:
        service.reconcile(p['id'], request)
    assert error.value.code == 'currency_mismatch'


def test_statement_requires_used_zero_balances_and_keeps_currencies_separate(setup):
    _, service, p, mapping = setup
    result = confirm(service, p['id'], body(setup, exchange_rows()))
    rows = [dict(as_of_date='2026-03-01', record_type='cash', currency=c, amount=a) for c, a in [('EUR', '598.00'), ('USD', '440.00')]]
    def statement(rows):
        return ReconciliationInput(expected_revision=result['context']['portfolio_revision'], format_id='atlas-statement-v2', source='Fixture D6', source_account='DEMO-D6', as_of_date='2026-03-01', complete_statement=True, mapping=mapping, csv=sheet(STATEMENT_COLUMNS, rows))
    with pytest.raises(BookError) as error:
        service.reconcile(p['id'], statement(rows[:1]))
    assert error.value.code == 'incomplete_statement'
    matching = confirm(service, p['id'], statement(rows), 'reconcile')
    assert matching['status'] == 'matched'
    assert {r['currency'] for r in matching['differences']} == {'EUR', 'USD'}
    rows[1]['amount'] = '441.00'
    different = confirm(service, p['id'], statement(rows), 'reconcile')
    assert different['status'] == 'differences'
    assert cash(service.read(p['id']), 'USD')['cash'] == '440.00'
    # A position present only in the reference still has its catalog currency.
    rows.append(dict(as_of_date='2026-03-01', record_type='position', listing_ref='USD', currency='USD', quantity='1'))
    assert service.reconcile(p['id'], statement(rows))['differences'][-1]['currency'] == 'USD'


def test_correction_cannot_remove_funding_for_later_usd_purchase(setup):
    store, service, p, _ = setup
    result = confirm(service, p['id'], body(setup, exchange_rows() + [row('buy', day_sequence='3', listing_ref='USD', currency='USD', quantity='1', unit_price='100', gross_amount='100.00')]))
    exchange = next(e for e in result['entries'] if e['event']['kind'] == 'fx_exchange')
    request = CorrectionInput(expected_revision=2, event_id=exchange['event']['id'], action='void', reason='Prueba de dependencia USD')
    before = dump(store.path)
    with pytest.raises(BookError) as error:
        service.correct(p['id'], request)
    assert error.value.code == 'insufficient_cash'
    assert dump(store.path) == before


def test_two_confirmations_and_failure_before_audit_are_atomic(setup, monkeypatch):
    store, service, p, _ = setup
    request = body(setup, exchange_rows())
    preview = service.import_movements(p['id'], request)
    commit = request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']})
    before = dump(store.path)
    real_audit = UnitOfWork.audit
    def fail(work, event, *args, **kwargs):
        if event == 'book.import_confirmed': raise RuntimeError('simulated commit failure')
        return real_audit(work, event, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(UnitOfWork, 'audit', fail)
        with pytest.raises(RuntimeError): service.import_movements(p['id'], commit)
    assert dump(store.path) == before
    barrier = Barrier(2)
    def submit():
        barrier.wait()
        try: return service.import_movements(p['id'], commit)['committed']
        except RevisionConflict: return 'conflict'
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        outcomes = [f.result() for f in futures]
    assert outcomes.count(True) == 1 and outcomes.count('conflict') == 1
    assert service.read(p['id'])['total'] == 2


def test_usd_dividend_right_payment_split_and_historical_cut(setup):
    store, service, p, mapping = setup
    confirm(service, p['id'], body(setup, [row('deposit', currency='USD', gross_amount='1100.00'), row('buy', day_sequence='2', currency='USD', listing_ref='USD', quantity='100', unit_price='10', gross_amount='1000.00')]))
    corp = CorporateService(store, multicurrency=True)
    csv_events = sheet(EVENT_COLUMNS, [dict(external_id='dividend', event_type='dividend', listing_ref='USD', effective_date='2026-01-10', payment_date='2026-01-20', gross_per_unit='0.50', currency='USD', source_reference='Fixture sintético D6'), dict(external_id='split', event_type='split', listing_ref='USD', effective_date='2026-02-01', ratio_numerator='2', ratio_denominator='1', currency='USD', source_reference='Fixture sintético D6')])
    request = CorporateInput(expected_revision=0, format_id='atlas-corporate-events-v1', source='Fixture D6', mapping=mapping, verified=True, evidence='Ejemplo ficticio comprobado', csv=csv_events)
    preview = corp.import_events(request)
    catalog = corp.import_events(request.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    dividend = next(e for e in catalog['events'] if e['event_type'] == 'dividend')
    split = next(e for e in catalog['events'] if e['event_type'] == 'split')
    review = CorporateReview(event_revision=1, day_sequence=10, evidence='100 títulos acreditados por el fixture sintético', eligible_quantity='100')
    def application_request(event, revision, review, csv=''):
        return CorporateApplicationInput(expected_revision=revision, event_id=event['id'], source='Fixture D6', source_account='DEMO-D6', review=review, csv=csv)
    right = confirm(corp, p['id'], application_request(dividend, 2, review), 'apply')
    assert right['pending_receivables_by_currency'] == [{'currency':'EUR','amount':'0.00'},{'currency':'USD','amount':'50.00'}]
    payment = sheet(MOVEMENT_COLUMNS, [row('dividend_payment', date='2026-01-20', day_sequence='10', listing_ref='ASSET', currency='USD', gross_amount='50.00', fee_amount='0.50', tax_amount='9.50', corporate_event_ref='EVENT')])
    paid = confirm(corp, p['id'], application_request(dividend, 3, review, payment), 'apply')
    assert cash(paid, 'USD')['cash'] == '140.00'
    assert paid['pending_receivables_by_currency'][-1]['amount'] == '0.00'
    split_row = sheet(MOVEMENT_COLUMNS, [row('split', date='2026-02-01', day_sequence='10', listing_ref='ASSET', currency='USD', ratio_numerator='2', ratio_denominator='1', corporate_event_ref='EVENT')])
    applied = confirm(corp, p['id'], application_request(split, 4, review.model_copy(update={'eligible_quantity':None}), split_row), 'apply')
    assert applied['balance']['positions'][0] == dict(listing_id=mapping['USD'], currency='USD', quantity='200', cost_basis='1000')
    assert corp.read(p['id'], '2026-01-15')['pending_receivables_by_currency'][-1]['amount'] == '50.00'
    assert cash(corp.read(p['id'], '2026-01-15'), 'USD')['cash'] == '100.00'
    assert CorporateService(store).catalog()['events'] == []
    with pytest.raises(BookError): CorporateService(store).version(dividend['id'], 1)
    with pytest.raises(BookError): CorporateService(store).read(p['id'])
    with TestClient(create_app(store.path.parent, run_worker=False)) as client:
        native = client.get(f"/api/v2/portfolios/{p['id']}/corporate-actions")
        assert native.status_code == 200, native.text
        assert native.json()['applications'][0]['event_snapshot']['currency'] == 'USD'
        assert client.get('/api/v2/corporate-events').json()['total'] == 2
        assert client.get('/api/corporate-events').json()['total'] == 0
        document = client.get(f"/api/v2/portfolios/{p['id']}/corporate-documents/{applied['document_id']}")
        assert document.status_code == 200, document.text


def test_legacy_multicurrency_adapter_keeps_eur_statement_and_rejects_usd(setup):
    store, service, _, mapping = setup
    p = PortfolioService(store).create('Heredada')
    reference = ReconciliationInput(expected_revision=p['revision'], format_id='atlas-statement-v2',
        source='Fixture D6', source_account='DEMO-D6', as_of_date='2026-03-01', complete_statement=True,
        mapping={}, csv=sheet(STATEMENT_COLUMNS, [dict(as_of_date='2026-03-01', record_type='cash', currency='EUR', amount='0.00')]))
    preview = service.reconcile(p['id'], reference)
    assert preview['status'] == 'matched'
    assert preview['differences'][0]['currency'] == 'EUR'
    with pytest.raises(BookError):
        service.reconcile(p['id'], reference.model_copy(update={'mapping': {'USD':mapping['USD']}}))
    usd = dict(as_of_date='2026-03-01', record_type='cash', currency='USD', amount='0.00')
    with pytest.raises(BookError):
        service.reconcile(p['id'], reference.model_copy(update={'csv': reference.csv + sheet(STATEMENT_COLUMNS, [usd]).split('\n', 1)[1]}))


def test_exhausted_currency_still_requires_zero_cash_statement(setup):
    _, service, p, mapping = setup
    result = confirm(service, p['id'], body(setup, [row('deposit', currency='USD', gross_amount='1.00'),
        row('withdrawal', day_sequence='2', currency='USD', gross_amount='1.00')]))
    request = ReconciliationInput(expected_revision=result['context']['portfolio_revision'], format_id='atlas-statement-v2',
        source='Fixture D6', source_account='DEMO-D6', as_of_date='2026-03-01', complete_statement=True, mapping=mapping,
        csv=sheet(STATEMENT_COLUMNS, [dict(as_of_date='2026-03-01', record_type='cash', currency='EUR', amount='0.00')]))
    with pytest.raises(BookError, match='Falta efectivo USD'):
        service.reconcile(p['id'], request)


def test_eur_book_with_usd_statement_row_keeps_native_document_and_rejects_old_client(setup):
    store, service, p, _ = setup
    request = ReconciliationInput(expected_revision=p['revision'], format_id='atlas-statement-v2',
        source='Fixture D6', source_account='DEMO-D6', as_of_date='2026-03-01', complete_statement=True,
        csv=sheet(STATEMENT_COLUMNS, [dict(as_of_date='2026-03-01', record_type='cash', currency=currency, amount='0.00') for currency in ('EUR', 'USD')]))
    result = confirm(service, p['id'], request, 'reconcile')
    assert result['status'] == 'matched'
    assert len(result['balance']['balances']) == 1
    with TestClient(create_app(store.path.parent, run_worker=False)) as client:
        path = f"/portfolios/{p['id']}/book-documents/{result['document_id']}"
        native = client.get('/api/v2' + path)
        assert native.status_code == 200, native.text
        assert native.json()['differences'][1]['currency'] == 'USD'
        old = client.get('/api' + path)
        assert old.status_code == 422, old.text
        assert old.json()['detail'][0]['type'] == 'unsupported_currency'


def test_http_new_contract_and_local_write_guard_preserve_eur_api(setup):
    store, service, p, _ = setup
    app = create_app(store.path.parent, run_worker=False)
    with TestClient(app) as client:
        path = f"/api/v2/portfolios/{p['id']}"
        request = body(setup, exchange_rows()).model_dump()
        assert client.post(path + '/imports', json=request).status_code == 403
        old = client.get(f"/api/portfolios/{p['id']}/book").json()
        assert old['balance']['cash'] == '0.00' and 'balances' not in old['balance']
        preview = client.post(path + '/imports', json=request, headers=LOCAL)
        assert preview.status_code == 200, preview.text
        response = client.post(path + '/imports', json={**request, 'commit':True,'preview_token':preview.json()['preview_token']}, headers=LOCAL)
        assert response.status_code == 200, response.text
        assert cash(response.json(), 'USD')['cash'] == '440.00'
        assert client.get(f"/api/portfolios/{p['id']}/book").status_code == 422
        record = client.get(path + '/book-documents/' + response.json()['document_id'])
        assert record.status_code == 200, record.text
        assert record.json()['balance']['balances'][1]['currency'] == 'USD'
        assert client.post(path + '/imports', json={**request,'commit':True,'preview_token':preview.json()['preview_token']}, headers=LOCAL).status_code == 409


def test_schema_five_migration_is_additive_reopenable_and_old_code_rejects(setup, monkeypatch):
    store, _, _, _ = setup
    with closing(sqlite3.connect(store.path)) as db, db:
        for table in reversed(DDL): db.execute(f'DROP TABLE {table}')
        db.execute('PRAGMA user_version=4')
    before = dump(store.path)
    Store(store.path)
    after = dump(store.path)
    assert all(after[t] == data for t, data in before.items())
    assert all(after[t] == [] for t in DDL)
    Store(store.path)
    assert dump(store.path) == after
    folder = create_backup(store.path, store.path.parent / 'backups')
    assert validate_backup(folder)['schema']['user_version'] == 5
    monkeypatch.setattr('atlas_quant.store.SCHEMA_VERSION', 4)
    with pytest.raises(ValueError, match='más nuevo'): Store(store.path)
    assert dump(store.path) == after

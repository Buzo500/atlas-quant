"""D5 economic oracles, coherent revisions, transactions and public contracts."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
from threading import Barrier
import json

import pytest
from fastapi.testclient import TestClient

from atlas_quant.app import create_app
from atlas_quant.book import BookError, MOVEMENT_COLUMNS
from atlas_quant.book_contracts import CorporateReview, CorrectionInput
from atlas_quant.book_service import BookService
from atlas_quant.corporate import EVENT_COLUMNS
from atlas_quant.corporate_contracts import CorporateInput, CorporateRevisionInput, CorporateApplicationInput
from atlas_quant.corporate_service import CorporateService
from atlas_quant.portfolios import PortfolioService
from atlas_quant.catalog import RevisionConflict
from atlas_quant.store import Store
from test_book_d4 import setup, request, confirm, movements, csv_text, dump, LOCAL

ORACLES = json.loads((Path(__file__).parents[2] / 'docs/fixtures/v0_4_d5_referencias.json').read_text(encoding='utf-8'))['cases']


def seed(setup, quantity='100', price='1', fee='0.00'):
    confirm(setup, request(setup, [dict(kind='deposit', gross_amount='10000.00'),
        dict(kind='buy', quantity=quantity, unit_price=price, gross_amount=str(D(quantity)*D(price)), fee_amount=fee)]))


def event_request(setup, kind='dividend', **changes):
    store, _, _, mapping = setup
    row = dict.fromkeys(EVENT_COLUMNS, '')
    row.update(external_id='div-1' if kind == 'dividend' else 'split-1', event_type=kind, listing_ref='ASSET',
        effective_date='2026-01-10', payment_date='2026-01-20' if kind == 'dividend' else '',
        gross_per_unit='0.50' if kind == 'dividend' else '', currency='EUR',
        ratio_numerator='2' if kind == 'split' else '', ratio_denominator='1' if kind == 'split' else '',
        source_reference='Documento sintético D5')
    row.update(changes)
    return CorporateInput(expected_revision=CorporateService(store).catalog()['revision'],
        format_id='atlas-corporate-events-v1', source='Eventos sintéticos',
        csv=csv_text(EVENT_COLUMNS, [row]), mapping=mapping, verified=True, evidence='Fixture de aceptación')


def commit_event(setup, body=None):
    store = setup[0]
    service = CorporateService(store)
    body = body or event_request(setup)
    preview = service.import_events(body)
    result = service.import_events(body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    return result['events'][-1] if len(result['events']) == 1 else next(e for e in result['events'] if e['id'] not in {
        x['id'] for x in preview['events'] if x['event_type'] != ('split' if 'split-1' in body.csv else 'dividend')})


def review(event, quantity='100', **changes):
    values = dict(event_revision=event['revision'], day_sequence=10, evidence='Elegibilidad/orden acreditados por fixture',
                  eligible_quantity=quantity if event['event_type'] == 'dividend' else None)
    return CorporateReview(**{**values, **changes})


def application_body(setup, event, **changes):
    store, _, portfolio, _ = setup
    values = dict(expected_revision=PortfolioService(store).read(portfolio['id'])['portfolio']['revision'],
        event_id=event['id'], source='Fixture', source_account='DEMO-01', review=review(event))
    return CorporateApplicationInput(**{**values, **changes})


def apply(setup, body):
    service, ident = CorporateService(setup[0]), setup[2]['id']
    preview = service.apply(ident, body)
    return service.apply(ident, body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))


def corporate_csv(event, *, external='payment', date=None, gross='50.00', tax='0.00', fee='0.00', linked=True):
    row = dict.fromkeys(MOVEMENT_COLUMNS, '')
    kind = event['event_type']
    row.update(external_id=external, date=date or (event['payment_date'] if kind == 'dividend' else event['effective_date']),
               day_sequence='10', kind='dividend_payment' if kind == 'dividend' else 'split', listing_ref='ASSET',
               currency='EUR', corporate_event_ref='EVENT' if linked else '')
    if kind == 'dividend':
        row.update(gross_amount=gross, fee_amount=fee, fee_currency='EUR', tax_amount=tax, tax_currency='EUR')
    else:
        row.update(ratio_numerator=str(event['ratio_numerator']), ratio_denominator=str(event['ratio_denominator']))
    return csv_text(MOVEMENT_COLUMNS, [row])


@pytest.mark.parametrize('oracle', [c for c in ORACLES if c['kind'] == 'dividend'], ids=lambda c: c['id'])
def test_dividend_oracles_and_eligibility_at_ex_not_payment(setup, oracle):
    seed(setup, oracle['eligible_quantity'])
    event = commit_event(setup, event_request(setup, gross_per_unit=oracle['gross_per_unit']))
    result = apply(setup, application_body(setup, event, review=review(event, oracle['eligible_quantity'])))
    assert D(result['pending_receivables']) == D(oracle['expected']['gross'])
    if 'quantity_sold_after_ex_date' in oracle or 'quantity_bought_after_ex_date' in oracle:
        quantity = oracle.get('quantity_sold_after_ex_date', oracle.get('quantity_bought_after_ex_date'))
        kind = 'sell' if 'quantity_sold_after_ex_date' in oracle else 'buy'
        confirm(setup, request(setup, [dict(external_id='after-ex', date='2026-01-15', kind=kind,
            quantity=quantity, unit_price='1', gross_amount=quantity)], as_of_date='2026-01-15'))
    before = setup[1].read(setup[2]['id'])['balance']
    paid = apply(setup, application_body(setup, event, review=review(event, oracle['eligible_quantity']),
        csv=corporate_csv(event, gross=oracle['expected']['gross'], tax=oracle['tax'], fee=oracle['fee'])))
    assert D(paid['balance']['cash']) - D(before['cash']) == D(oracle['expected']['cash_delta'])
    assert D(paid['pending_receivables']) == 0
    assert paid['balance']['net_contributions'] == before['net_contributions']
    assert paid['applications'][0]['status'] == 'reconciled'
    assert CorporateService(setup[0]).read(setup[2]['id'], '2026-01-19')['pending_receivables'] == oracle['expected']['gross']
    assert paid['unlinked_payments'] == []


@pytest.mark.parametrize('oracle', [c for c in ORACLES if c['kind'] == 'split'], ids=lambda c: c['id'])
def test_split_oracles_preserve_cost_without_prices(setup, oracle):
    fee = '2.00' if oracle['id'] == 'split_2_for_1' else '0.00'
    price = (D(oracle['cost'])-D(fee))/D(oracle['quantity'])
    seed(setup, oracle['quantity'], str(price), fee)
    event = commit_event(setup, event_request(setup, 'split', ratio_numerator=str(oracle['numerator']), ratio_denominator=str(oracle['denominator'])))
    before = setup[1].read(setup[2]['id'])['balance']
    result = apply(setup, application_body(setup, event, review=review(event, fraction_evidence='La cuenta conserva la fracción'), csv=corporate_csv(event)))
    position = result['balance']['positions'][0]
    assert D(position['quantity']) == D(oracle['expected']['quantity'])
    assert D(position['cost_basis']) == D(oracle['cost'])
    assert result['balance']['cash'] == before['cash']
    assert result['balance']['net_contributions'] == before['net_contributions']
    assert result['applications'][0]['price_status'] == 'not_accredited'


def test_link_existing_payment_no_second_cash_and_historical_revision(setup):
    seed(setup)
    event = commit_event(setup)
    csv = corporate_csv(event, linked=False)
    confirm(setup, request(setup, csv=csv, as_of_date='2026-01-20', unaccredited_payments={'payment': 'Extracto del cobro, exfecha aún sin evidencia'}))
    service, ident = CorporateService(setup[0]), setup[2]['id']
    before = service.read(ident)
    assert before['unlinked_payments']
    old_revision = before['portfolio_revision']
    result = apply(setup, application_body(setup, event, movement_id=before['unlinked_payments'][0]))
    assert result['balance'] == before['balance']
    assert result['unlinked_payments'] == []
    assert service.read(ident, revision=old_revision)['unlinked_payments'] == before['unlinked_payments']
    assert service.read(ident, '2026-01-15')['pending_receivables'] == '50.00'
    again = apply(setup, application_body(setup, event))
    assert again['balance'] == result['balance'] and len(again['applications']) == 1


def test_fraction_unrepresentable_and_unaccredited_fraction_leave_database_untouched(setup):
    seed(setup, '3')
    event = commit_event(setup, event_request(setup, 'split', ratio_numerator='1', ratio_denominator='7'))
    before = dump(setup[0].path)
    with pytest.raises(BookError, match='12 decimales'):
        CorporateService(setup[0]).apply(setup[2]['id'], application_body(setup, event, csv=corporate_csv(event)))
    assert dump(setup[0].path) == before


def test_split_between_ex_and_payment_keeps_original_right(setup):
    seed(setup, '10')
    dividend = commit_event(setup, event_request(setup, gross_per_unit='2.00'))
    apply(setup, application_body(setup, dividend, review=review(dividend, '10')))
    split = commit_event(setup, event_request(setup, 'split', effective_date='2026-01-15'))
    result = apply(setup, application_body(setup, split, review=review(split), csv=corporate_csv(split, external='split')))
    assert result['balance']['positions'][0]['quantity'] == '20'
    assert result['pending_receivables'] == '20.00'
    result = apply(setup, application_body(setup, dividend, review=review(dividend, '10'), csv=corporate_csv(dividend, gross='20.00')))
    assert result['pending_receivables'] == '0.00'


def test_corporate_sources_alias_duplicate_and_conflict(setup):
    service = CorporateService(setup[0])
    body = event_request(setup)
    event = commit_event(setup, body)
    again = body.model_copy(update={'expected_revision': service.catalog()['revision']})
    preview = service.import_events(again)
    assert preview['added'] == 0 and preview['duplicates'] == 1
    alias = again.model_copy(update={'source': 'Otra fuente', 'event_mapping': {'div-1': event['id']}})
    preview = service.import_events(alias)
    result = service.import_events(alias.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert len(result['events']) == 1 and len(result['sources']) == 2
    conflict = event_request(setup, gross_per_unit='1.00')
    before = dump(setup[0].path)
    with pytest.raises(BookError, match='ID de fuente'):
        service.import_events(conflict)
    assert dump(setup[0].path) == before


def test_same_date_distinct_ids_require_explicit_identity_decision(setup):
    commit_event(setup)
    body = event_request(setup, external_id='second-id')
    with pytest.raises(BookError, match='distinct_event_reason'):
        CorporateService(setup[0]).import_events(body)
    body = body.model_copy(update={'distinct_reasons': {'second-id': 'Dos distribuciones distintas según el fixture'}})
    assert CorporateService(setup[0]).import_events(body)['added'] == 1


@pytest.mark.parametrize('change,code', [
    ({'currency': 'USD'}, 'unsupported_corporate_event'),
    ({'gross_per_unit': '-1'}, 'invalid_decimal'),
    ({'gross_per_unit': 'NaN'}, 'invalid_decimal'),
    ({'gross_per_unit': '1000000000000000001'}, 'numeric_range'),
    ({'payment_date': '2026-01-01'}, 'corporate_dates'),
    ({'available_at': '2026-01-01'}, 'invalid_availability'),
    ({'available_at': '2999-01-01T00:00:00Z'}, 'invalid_availability'),
    ({'ratio_numerator': '2'}, 'incompatible_field'),
])
def test_invalid_event_fields_do_not_write(setup, change, code):
    before = dump(setup[0].path)
    with pytest.raises(BookError) as error:
        CorporateService(setup[0]).import_events(event_request(setup, **change))
    assert error.value.code == code
    assert dump(setup[0].path) == before


@pytest.mark.parametrize('field,value', [('effective_date', ''), ('effective_date', '2999-01-01')])
def test_incomplete_or_future_event_can_be_proposed_but_not_applied(setup, field, value):
    seed(setup)
    event = commit_event(setup, event_request(setup, **{field: value, 'payment_date': ''}))
    before = dump(setup[0].path)
    with pytest.raises(BookError):
        CorporateService(setup[0]).apply(setup[2]['id'], application_body(setup, event))
    assert dump(setup[0].path) == before


@pytest.mark.parametrize('mode', ['import', 'application', 'revision'])
def test_audit_failure_rolls_back_all_corporate_tables_and_book(setup, monkeypatch, mode):
    seed(setup)
    service = CorporateService(setup[0])
    if mode == 'import':
        body, action = event_request(setup), service.import_events
    else:
        event = commit_event(setup)
        if mode == 'application':
            body = application_body(setup, event, csv=corporate_csv(event))
            action = lambda b: service.apply(setup[2]['id'], b)
        else:
            body = CorporateRevisionInput(expected_revision=service.catalog()['revision'], event_id=event['id'],
                event_revision=1, action='cancel', reason='Cancelación de prueba')
            action = service.revise
    preview = action(body)
    before = dump(setup[0].path)
    def fail(*args):
        raise RuntimeError('audit failure')
    monkeypatch.setattr(Store, '_audit', staticmethod(fail))
    with pytest.raises(RuntimeError, match='audit failure'):
        action(body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert dump(setup[0].path) == before


def test_two_confirmations_have_one_effect(setup, monkeypatch):
    seed(setup)
    event = commit_event(setup)
    service, ident = CorporateService(setup[0]), setup[2]['id']
    body = application_body(setup, event, csv=corporate_csv(event))
    preview = service.apply(ident, body)
    commit = body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']})
    barrier, original = Barrier(2), service._check_token
    def synchronise(token, value):
        original(token, value)
        barrier.wait(timeout=5)
    monkeypatch.setattr(service, '_check_token', synchronise)
    def attempt():
        try:
            service.apply(ident, commit)
            return 'ok'
        except RevisionConflict:
            return 'conflict'
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        assert sorted(f.result() for f in futures) == ['conflict', 'ok']
    result = service.read(ident)
    assert result['balance']['cash'] == '9950.00'
    assert len(result['applications']) == 1


def test_payload_and_catalog_changes_invalidate_application_preview(setup):
    from atlas_quant.catalog import CatalogService
    seed(setup)
    event = commit_event(setup)
    service, ident = CorporateService(setup[0]), setup[2]['id']
    body = application_body(setup, event)
    preview = service.apply(ident, body)
    commit = body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']})
    with pytest.raises(RevisionConflict):
        service.apply(ident, commit.model_copy(update={'review': review(event, evidence='Otra evidencia')}))
    catalog = CatalogService(setup[0])
    catalog.add('instrument', dict(expected_revision=catalog.read()['revision'], name='Concurrente', source='Fixture'))
    with pytest.raises(RevisionConflict):
        service.apply(ident, commit)


def test_revision_does_not_rewrite_paid_right_and_blocks_incompatible_review(setup):
    seed(setup)
    event = commit_event(setup)
    original = apply(setup, application_body(setup, event, csv=corporate_csv(event)))
    service, ident = CorporateService(setup[0]), setup[2]['id']
    changed = event_request(setup, gross_per_unit='1.00')
    body = CorporateRevisionInput(expected_revision=service.catalog()['revision'], event_id=event['id'], event_revision=1,
        action='replace', reason='Rectificación acreditada', csv=changed.csv, mapping=changed.mapping, verified=True, evidence='Documento nuevo')
    preview = service.revise(body)
    result = service.revise(body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert service.version(event['id'], 1) == event
    read = service.read(ident)
    assert read['balance'] == original['balance']
    assert read['applications'][0]['status'] == 'outdated'
    before = dump(setup[0].path)
    with pytest.raises(BookError, match='pago completo'):
        service.apply(ident, application_body(setup, result['events'][0]))
    assert dump(setup[0].path) == before


def test_book_correction_requires_revalidation_of_dependent_right(setup):
    seed(setup)
    event = commit_event(setup)
    apply(setup, application_body(setup, event))
    store, books, portfolio, mapping = setup
    detail = books.read(portfolio['id'])
    original = next(e['event'] for e in detail['entries'] if e['event']['kind'] == 'buy')
    csv = movements([dict(external_id=original['external_id'], kind='buy', quantity='90', unit_price='1', gross_amount='90.00', day_sequence='2')])
    body = CorrectionInput(expected_revision=detail['context']['portfolio_revision'], event_id=original['id'], action='replace',
        reason='Cantidad rectificada', csv=csv, mapping=mapping)
    before = dump(store.path)
    with pytest.raises(BookError, match='historia modifica'):
        books.correct(portfolio['id'], body)
    assert dump(store.path) == before
    body = body.model_copy(update={'corporate_reviews': {event['id']: review(event, '90')}})
    preview = books.correct(portfolio['id'], body)
    books.correct(portfolio['id'], body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert CorporateService(store).read(portfolio['id'])['pending_receivables'] == '45.00'


def test_void_payment_restores_right_but_reimport_does_not_reactivate_cash(setup):
    seed(setup)
    event = commit_event(setup)
    apply(setup, application_body(setup, event, csv=corporate_csv(event)))
    store, books, portfolio, mapping = setup
    detail = books.read(portfolio['id'])
    payment = next(e['event'] for e in detail['entries'] if e['event']['kind'] == 'dividend_payment')
    body = CorrectionInput(expected_revision=detail['context']['portfolio_revision'], event_id=payment['id'], action='void', reason='Pago anulado con evidencia')
    preview = books.correct(portfolio['id'], body)
    books.correct(portfolio['id'], body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    result = CorporateService(store).read(portfolio['id'])
    assert result['pending_receivables'] == '50.00' and result['balance']['cash'] == '9900.00'
    result = confirm(setup, request(setup, csv=corporate_csv(event), as_of_date='2026-01-20', corporate_mapping={'EVENT': event['id']}))
    assert result['added'] == 0 and result['balance']['cash'] == '9900.00'


def test_separate_portfolio_applications(setup):
    seed(setup)
    event = commit_event(setup)
    apply(setup, application_body(setup, event))
    store, books, _, mapping = setup
    portfolio = PortfolioService(store).create('Segunda', 'atlas-accounting-v2')
    other = store, books, portfolio, mapping
    seed(other, '4')
    result = apply(other, application_body(other, event, review=review(event, '4'), csv=corporate_csv(event, gross='2.00')))
    assert result['pending_receivables'] == '0.00'
    assert CorporateService(store).read(setup[2]['id'])['pending_receivables'] == '50.00'


def test_public_contracts_write_guard_templates_and_documents(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    with TestClient(app) as client:
        catalog = client.get('/api/corporate-events').json()
        assert catalog['events'] == [] and catalog['revision'] == 0
        assert client.get('/api/templates/corporate-events').text.strip() == ','.join(EVENT_COLUMNS)
        assert client.post('/api/corporate-events/imports', json={}).status_code == 403
        assert client.post('/api/corporate-events/imports', headers=LOCAL, json={}).status_code == 422
        assert client.get('/api/corporate-documents').json()['documents'] == []
        assert client.get('/api/corporate-events/missing/versions/1').status_code == 404
        assert 'CorporateApplicationInput' in app.openapi()['components']['schemas']


def test_response_models_accept_real_full_preview(setup):
    from atlas_quant.corporate_contracts import CorporateApplicationPreview, CorporatePreview
    seed(setup)
    service = CorporateService(setup[0])
    assert CorporatePreview.model_validate(service.import_events(event_request(setup)))
    event = commit_event(setup)
    assert CorporateApplicationPreview.model_validate(service.apply(setup[2]['id'], application_body(setup, event, csv=corporate_csv(event))))


def test_movement_with_another_explicit_event_cannot_be_claimed(setup):
    from atlas_quant.corporate import link_movement
    seed(setup)
    event = commit_event(setup)
    result = apply(setup, application_body(setup, event, csv=corporate_csv(event)))
    entry = next(e for e in setup[1].read(setup[2]['id'])['entries'] if e['event']['kind'] == 'dividend_payment')
    other = {**event, 'id': 'other-event'}
    app = {**result['applications'][0], 'event_id': other['id'], 'event_snapshot': other, 'movement_key': None}
    with pytest.raises(BookError, match='identifica otro evento'):
        link_movement(app, entry)


def bind_prices(setup, **changes):
    from test_quality_d3 import bar
    data = dict(id='prices', version=1, name='Marcas sintéticas', source='Fixture', source_kind='observed',
                bars=[bar('2026-01-05'), bar('2026-01-12')],
                corporate_actions=[dict(symbol='TEST', date='2026-01-10', type='split', ratio='2:1')],
                quality_evidence={'TEST': {'price_basis': 'raw', 'basis_verified': True}})
    data.update(changes)
    setup[0].save_dataset(data)
    service = PortfolioService(setup[0])
    bindings = [dict(listing_id=setup[3]['ASSET'], dataset_id='prices', dataset_version=1, symbol='TEST')]
    preview = service.bind(setup[2]['id'], bindings)
    service.bind(setup[2]['id'], bindings, True, preview['preview_token'])
    return setup[0].get('dataset', 'prices')


@pytest.mark.parametrize('variant,expected', [('raw', 'compatible'), ('adjusted', 'not_accredited'), ('unverified', 'not_accredited'), ('before', 'not_accredited'), ('new_version', 'not_accredited'), ('cancelled', 'not_accredited')])
def test_split_price_compatibility_and_no_global_quality_promotion(setup, variant, expected):
    from atlas_quant.quality import report
    seed(setup)
    event = commit_event(setup, event_request(setup, 'split'))
    changes = {}
    if variant in {'adjusted', 'unverified'}:
        changes['quality_evidence'] = {'TEST': {'price_basis': 'split_adjusted' if variant == 'adjusted' else 'raw', 'basis_verified': variant != 'unverified'}}
    data = bind_prices(setup, **changes)
    original = deepcopy(data)
    quality = report(data, 'TEST')
    apply(setup, application_body(setup, event, csv=corporate_csv(event)))
    service = CorporateService(setup[0])
    if variant == 'new_version':
        setup[0].save_dataset({**data, 'version': 2})
    if variant == 'cancelled':
        body = CorporateRevisionInput(expected_revision=service.catalog()['revision'], event_id=event['id'], event_revision=1, action='cancel', reason='Cancelación acreditada')
        preview = service.revise(body)
        service.revise(body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    result = service.read(setup[2]['id'], '2026-01-10' if variant == 'before' else '2026-01-12')
    assert result['applications'][0]['price_status'] == expected
    frozen = setup[0].atomic(lambda w: w.dataset_version('prices', 1))
    assert frozen == original
    assert report(frozen, 'TEST') == quality
    assert quality['capabilities']['historical'] == 'blocked'


def test_price_change_during_confirmation_is_atomic_conflict(setup, monkeypatch):
    seed(setup)
    event = commit_event(setup, event_request(setup, 'split'))
    data = bind_prices(setup)
    service, ident = CorporateService(setup[0]), setup[2]['id']
    body = application_body(setup, event, csv=corporate_csv(event))
    preview = service.apply(ident, body)
    original = service._check_token
    def change_prices(token, value):
        original(token, value)
        setup[0].save_dataset({**data, 'version': 2})
    monkeypatch.setattr(service, '_check_token', change_prices)
    with pytest.raises(RevisionConflict):
        service.apply(ident, body.model_copy(update={'commit': True, 'preview_token': preview['preview_token']}))
    assert service.read(ident)['applications'] == []
    assert len(setup[1].read(ident)['entries']) == 2
    assert service.documents(ident)['total'] == 0

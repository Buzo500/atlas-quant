"""Public CSV boundary, independent numeric oracle and durable temporal gates."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from atlas_quant.app import create_app
from atlas_quant.catalog import CatalogService, RevisionConflict
from atlas_quant.lab_contracts import LabInput, LabOpenInput, LabReport
from atlas_quant.lab_service import LabService
from atlas_quant.market_contracts import MarketImport
from atlas_quant.market_service import MarketService
from atlas_quant.store import Store, UnitOfWork

LOCAL = {'X-Atlas-Client': 'local-v1'}


def fixture_request():
    days = [(date(2025, 1, 1)+timedelta(days=i)).isoformat() for i in range(14)]
    closes = [10, 10, 10, 12, 10, 8, 8]*2
    prices = ['date,listing_ref,open,high,low,close,volume,currency,available_at']
    sessions = ['date,open_at,close_at,open_available_at']
    for i, (day, close) in enumerate(zip(days, closes)):
        op = 8 if i in (6, 13) else 10
        prices.append(f'{day},ASSET,{op},{max(op,close)},{min(op,close)},{close},100,EUR,{day}T17:01:00Z')
        sessions.append(f'{day},{day}T09:00:00Z,{day}T17:00:00Z,{day}T09:00:00Z')
    market = dict(name='SMA EUR ficticia', source='Referencia sintética v0.6, todos los días abiertos', csv='\n'.join(prices),
        evidence=dict(symbol='ASSET', calendar_name='Calendario ficticio', market='TEST', timezone='UTC',
            calendar_source='Referencia sintética sin festivos', calendar_verified=True,
            calendar_csv='date,status,close_at\n'+'\n'.join(f'{d},open,{d}T17:00:00Z' for d in days),
            price_basis='raw', basis_verified=True, basis_source='Precios brutos ficticios'))
    protocol = dict(name='Referencia temporal ficticia', start_date=days[0], holdout_date=days[7], end_date=days[-1],
        fast=2, slow=3, sessions_csv='\n'.join(sessions), opening_source='Aperturas ficticias disponibles al abrir',
        event_free_source='Escenario sintético sin eventos corporativos', evidence_reviewed=True,
        config=dict(initial_cash_eur='1000', fixed_fee_eur='1', fee_bps='0', slippage_bps='0'))
    return market, protocol


@pytest.fixture
def lab(tmp_path):
    store = Store(tmp_path/'atlas.sqlite3')
    catalog = CatalogService(store)
    c = catalog.add('instrument', dict(expected_revision=0, name='Activo ficticio SMA', source='Fixture sintético'))
    c = catalog.add('listing', dict(expected_revision=c['revision'], instrument_id=c['instruments'][0]['id'], currency='EUR', market='TEST'))
    market, protocol = fixture_request()
    request = MarketImport(**market, listing_id=c['listings'][0]['id'])
    service = MarketService(store)
    preview = service.import_series('prices', request)
    series = service.import_series('prices', request.model_copy(update=dict(commit=True, preview_token=preview['preview_token'])))['series']
    body = LabInput(**protocol, series_id=series['id'], series_version=series['version'])
    return store, LabService(store), body


def open_request(ident):
    return LabOpenInput(protocol_hash=ident, acknowledge_exposure=True)


def test_independent_arithmetic_and_no_holdout_leak(lab):
    store, service, body = lab
    before = store.read(lambda w: (w.portfolio_list(), w.catalog()))
    result = service.create(body)
    LabReport.model_validate(result)
    assert result['holdout'] is None and result['protocol']['opened'] is False
    assert result['development']['end_date'] < body.holdout_date
    metrics = result['development']['metrics']
    assert [m['final_nav_eur'] for m in metrics] == ['800', '801', '1000']
    assert [m['fees_eur'] for m in metrics] == ['2.00', '1.00', '0.00']
    # Separate initial capital and warm-up produce the same independent period.
    opened = service.open_holdout(result['protocol']['id'], open_request(result['protocol']['id']))
    assert opened['holdout']['metrics'] == metrics
    assert store.read(lambda w: (w.portfolio_list(), w.catalog())) == before
    assert service.reproduce(result['protocol']['id']) == dict(id=result['protocol']['id'], development_matches=True, holdout_matches=True)


def test_idempotent_create_open_and_restart(lab):
    store, service, body = lab
    first = service.create(body)
    assert service.create(body) == first
    ident = first['protocol']['id']
    opened = service.open_holdout(ident, open_request(ident))
    assert service.open_holdout(ident, open_request(ident)) == opened
    restarted = LabService(Store(store.path))
    assert restarted.read(ident) == opened
    assert len(restarted.history()['items']) == 1
    events = store.read(lambda w: [r[0] for r in w.db.execute("SELECT event FROM audit WHERE event LIKE 'lab.%'")])
    assert events == ['lab.development_saved', 'lab.holdout_opened']


@pytest.mark.parametrize('change', [
    {'evidence_reviewed': False}, {'fast': 3}, {'holdout_date': '2025-01-03'},
    {'opening_source': '  '}, {'sessions_csv': 'date,open_at,close_at,open_available_at\n'},
])
def test_invalid_inputs_leave_no_protocol(lab, change):
    store, service, body = lab
    with pytest.raises(ValueError):
        service.create(LabInput.model_validate({**body.model_dump(), **change}))
    assert service.history()['items'] == []


@pytest.mark.parametrize('replace', [
    ('2025-01-01T09:00:00Z', '2025-01-01T08:59:00Z'),
    ('2025-01-01T17:00:00Z', '2025-01-01T18:00:00Z'),
])
def test_inconsistent_open_evidence_rejected(lab, replace):
    _, service, body = lab
    # Only availability for the first case, not the actual open time.
    csv = body.sessions_csv
    if '08:59' in replace[1]:
        csv = csv.replace('2025-01-01T17:00:00Z,2025-01-01T09:00:00Z', '2025-01-01T17:00:00Z,2025-01-01T08:59:00Z')
    else:
        csv = csv.replace(*replace)
    with pytest.raises(ValueError):
        service.create(body.model_copy(update={'sessions_csv': csv}))


def test_two_candidates_share_reserved_holdout_but_only_one_can_open(lab):
    _, service, body = lab
    a = service.create(body)['protocol']['id']
    b = service.create(body.model_copy(update={'name': 'Otro candidato'}))['protocol']['id']
    service.open_holdout(a, open_request(a))
    with pytest.raises(RevisionConflict, match='ya calculado'):
        service.open_holdout(b, open_request(b))
    assert service.read(b)['holdout'] is None
    with pytest.raises(RevisionConflict):
        service.create(body.model_copy(update={'name': 'No volver a etiquetar como nuevo'}))


def test_development_cannot_invade_an_existing_reservation(lab):
    _, service, body = lab
    service.create(body)
    with pytest.raises(RevisionConflict, match='invade'):
        service.create(body.model_copy(update={'name': 'Corte posterior', 'holdout_date': '2025-01-10'}))


def test_audit_failure_rolls_back_protocol_and_temporal_locks(lab, monkeypatch):
    _, service, body = lab
    original = UnitOfWork.audit
    def fail(work, event, *args, **kwargs):
        if event.startswith('lab.'):
            raise RuntimeError('audit unavailable')
        return original(work, event, *args, **kwargs)
    monkeypatch.setattr(UnitOfWork, 'audit', fail)
    with pytest.raises(RuntimeError):
        service.create(body)
    assert service.history()['items'] == []
    monkeypatch.setattr(UnitOfWork, 'audit', original)
    assert service.create(body)['holdout'] is None


def test_concurrent_holdout_open_returns_one_immutable_result(lab, monkeypatch):
    store, service, body = lab
    ident = service.create(body)['protocol']['id']
    from atlas_quant import lab_service
    real, barrier = lab_service.period, Barrier(2)
    def together(*args):
        result = real(*args)
        barrier.wait(timeout=10)
        return result
    monkeypatch.setattr(lab_service, 'period', together)
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(LabService(Store(store.path)).open_holdout, ident, open_request(ident)) for _ in range(2)]
        values = [f.result() for f in futures]
    assert values[0] == values[1]
    assert store.read(lambda w: w.db.execute("SELECT COUNT(*) FROM audit WHERE event='lab.holdout_opened'").fetchone()[0]) == 1


def test_http_strict_contracts_history_and_explicit_open(lab):
    store, _, body = lab
    with TestClient(create_app(store.path.parent, run_worker=False)) as client:
        rejected = client.post('/api/lab/protocols', json=body.model_dump(mode='json'))
        assert rejected.status_code == 403
        response = client.post('/api/lab/protocols', json=body.model_dump(mode='json'), headers=LOCAL)
        assert response.status_code == 200, response.text
        ident = response.json()['protocol']['id']
        assert 'frozen' not in response.json() and 'inputs' not in response.json()
        assert client.get('/api/lab/protocols').json()['items'][0]['id'] == ident
        assert client.post(f'/api/lab/protocols/{ident}/holdout', json=dict(protocol_hash=ident, acknowledge_exposure=1), headers=LOCAL).status_code == 422
        opened = client.post(f'/api/lab/protocols/{ident}/holdout', json=open_request(ident).model_dump(), headers=LOCAL)
        assert opened.status_code == 200, opened.text
        assert client.post(f'/api/lab/protocols/{ident}/reproduce', headers=LOCAL).json()['holdout_matches'] is True


def test_reproduce_never_computes_a_reserved_holdout(lab, monkeypatch):
    _, service, body = lab
    ident = service.create(body)['protocol']['id']
    from atlas_quant import lab_service
    real = lab_service.period
    def development_only(frozen, request, holdout):
        assert holdout is False
        return real(frozen, request, holdout)
    monkeypatch.setattr(lab_service, 'period', development_only)
    assert service.reproduce(ident)['holdout_matches'] is None


def test_concurrent_distinct_candidates_cannot_both_expose_same_holdout(lab, monkeypatch):
    store, service, body = lab
    ids = [service.create(body.model_copy(update={'name': n}))['protocol']['id'] for n in ('Candidato uno', 'Candidato dos')]
    from atlas_quant import lab_service
    real, barrier = lab_service.period, Barrier(2)
    def together(*args):
        result = real(*args)
        barrier.wait(timeout=10)
        return result
    monkeypatch.setattr(lab_service, 'period', together)
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(LabService(Store(store.path)).open_holdout, i, open_request(i)) for i in ids]
        successes = 0
        for f in futures:
            try:
                f.result()
                successes += 1
            except RevisionConflict:
                pass
    assert successes == 1


def test_known_corporate_event_blocks_explicit_event_free_assertion(lab, monkeypatch):
    store, service, body = lab
    listing = store.read(lambda w: w.catalog()['listings'][0]['id'])
    monkeypatch.setattr(UnitOfWork, 'corporate_state', lambda w: dict(revision=1, sources=[], events=[
        dict(listing_id=listing, cancelled=False, ex_date='2025-01-04', event_type='dividend')]))
    with pytest.raises(ValueError, match='corporativos'):
        service.create(body)


def test_source_context_change_during_compute_rolls_back(lab, monkeypatch):
    _, service, body = lab
    original, calls = service._snapshot, 0
    def changed(work, request):
        nonlocal calls
        value = original(work, request)
        calls += 1
        if calls > 1:
            value[2]['revision'] += 1
        return value
    monkeypatch.setattr(service, '_snapshot', changed)
    with pytest.raises(RevisionConflict, match='evidencia'):
        service.create(body)
    assert service.history()['items'] == []


def test_missing_open_does_not_get_replaced_with_close(lab):
    _, service, body = lab
    csv = body.sessions_csv.replace('2025-01-05T17:00:00Z,2025-01-05T09:00:00Z', '2025-01-05T17:00:00Z,')
    result = service.create(body.model_copy(update={'sessions_csv': csv}))['development']
    assert result['metrics'][0]['fills'] == 0
    assert result['metrics'][0]['final_nav_eur'] == '1000'
    assert result['expired'] == 1


def test_source_version_revision_cannot_reset_exposure(lab):
    store, service, body = lab
    ident = service.create(body)['protocol']['id']
    service.open_holdout(ident, open_request(ident))
    data = store.read(lambda w: w.market_version('prices', body.series_id, 1))
    data['version'] = 2
    store.atomic(lambda w: w.save_market_version(data))
    with pytest.raises(RevisionConflict, match='ya calculado'):
        service.create(body.model_copy(update={'series_version': 2}))

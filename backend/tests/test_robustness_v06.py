"""Paired numeric oracles, frozen evidence, no reserve access and atomic publication."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import date, timedelta
from decimal import localcontext, ROUND_UP
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient
from atlas_quant.app import create_app
from atlas_quant.candidate_contracts import CandidateInput, CandidateRevisionInput
from atlas_quant.candidate_service import CandidateService
from atlas_quant.catalog import CatalogService, RevisionConflict
from atlas_quant.computation import _SLOTS, ComputationBusy
from atlas_quant.lab_contracts import LabInput
from atlas_quant.lab_service import LabService
from atlas_quant.market_contracts import MarketImport
from atlas_quant.market_service import MarketService
from atlas_quant.robustness import (evaluate, indices_from_draws, stationary_means, pp, prepare, seed_for)
from atlas_quant.robustness_contracts import RobustnessInput, RobustnessReport
from atlas_quant.robustness_service import RobustnessService
from atlas_quant.store import Store, UnitOfWork
from test_lab_v06 import lab, LOCAL  # noqa: F401
from test_lab_v06 import fixture_request


def numeric_snapshot(n=504):
    dates = [(date(2020, 1, 1)+timedelta(days=i)).isoformat() for i in range(n+3)]
    return dict(protocol=dict(slow=3, holdout_date='2030-01-01', start_date=dates[0]),
        session_dates=dates, config=dict(policy='sma-economics-eur-v1', initial_cash_eur='1000'),
        source=dict(currency='EUR', price_basis='raw', basis_verified=True, corporate_policy='verified-event-free-v1'), development=dict(sessions=len(dates), report_hash='a'*64,
            trades=[dict(strategy='Comprar y mantener', side='buy', date=dates[0])],
            curve=[dict(date=d, sma_eur='1000', buy_hold_eur='1000', cash_eur='1000') for d in dates]))


def statistical_request(store, ident):
    candidate = CandidateService(store).create(CandidateInput(name='Consulta de incertidumbre',
        hypothesis='Hipótesis sintética de referencia.', reason='Todos los ensayos sintéticos vinculados.', protocol_ids=[ident]))
    return RobustnessInput(protocol_id=ident, candidate_id=candidate['candidate_id'], revision=candidate['revision'],
        revision_hash=candidate['revision_hash'], related_protocol_ids=[ident],
        reason='Medir incertidumbre sobre el desarrollo conservado.', acknowledge_exploratory=True)


def test_circular_runs_and_paired_reference():
    # Start at 3, wrap at 4, restart at 2, then continue at 3.
    starts = np.array([3, 1, 2, 0])
    indices = indices_from_draws(starts, np.array([False, True, False]))
    assert indices.tolist() == [3, 0, 2, 3]
    pairs = np.array([[1., 10.], [2., 20.], [3., 30.], [4., 40.]])
    assert np.mean(pairs[indices, 0]-pairs[indices, 1]) == (-36-9-27-36)/4
    # Perfectly paired equal series always have zero excess, even after resampling.
    equal = np.c_[np.arange(10), np.arange(10)]
    means, _ = stationary_means(equal, 5, 17, replicas=12)
    assert means.tolist() == [0.]*12


def test_fixed_prng_sequence_and_linear_quantile_reference():
    pairs = np.c_[np.arange(4)/10, np.zeros(4)]
    means, fingerprint = stationary_means(pairs, 2, 17, replicas=4)
    # Scalar independent reconstruction with the declared PCG call order.
    rng = np.random.Generator(np.random.PCG64(17))
    expected = []
    for _ in range(4):
        starts, resets = rng.integers(0, 4, size=4, dtype=np.int64), rng.random(3)
        indices = [int(starts[0])]
        for i in range(1,4): indices.append(int(starts[i]) if resets[i-1] < .5 else (indices[-1]+1)%4)
        expected.append(sum(i/10 for i in indices)/4)
    assert means == pytest.approx(expected, abs=1e-15)
    assert fingerprint == '897cf9280f5cb26dc8bcf186b05d4c22efed77dc4a1f81c181bae05a4df154d4'
    assert np.quantile([0., 1., 2., 3.], [.025,.975], method='linear') == pytest.approx([.075,2.925])
    assert pp(.0001234) == '0.012340000000'


def test_constant_excess_full_policy_reproduces_and_does_not_select_a_winner():
    snapshot = numeric_snapshot()
    result = evaluate(snapshot)
    assert result['status'] == 'exploratory'
    assert result['intervals'] == 504 and result['work_indices'] == 7_560_000
    assert result['mean_excess_pp'] == '0.000000000000'
    assert result['principal_includes_zero'] and not result['direction_changes']
    assert [l['length'] for l in result['lengths']] == [5,10,20]
    assert all(l['lower_pp'] == l['upper_pp'] == '0.000000000000' for l in result['lengths'])
    assert result['start_date'] == snapshot['session_dates'][3]
    with localcontext() as context:
        context.prec, context.rounding = 6, ROUND_UP
        assert evaluate(snapshot) == result
    assert len({seed_for('a'*64, L) for L in [5,10,20]}) == 3
    assert seed_for('a'*64, 10) != seed_for('b'*64, 10)
    assert 'p_value' not in result and 'approved' not in result


@pytest.mark.parametrize('value', [None, '0', '-1', 'NaN', 'Infinity', 'bad'])
def test_bad_nav_including_preceding_close_is_not_dropped(value):
    snapshot = numeric_snapshot()
    snapshot['development']['curve'][2]['sma_eur'] = value
    result = evaluate(snapshot)
    assert result['status'] == 'no_evaluable' and result['lengths'] == []
    assert any('NAV' in r for r in result['reasons'])


@pytest.mark.parametrize('case', ['gap', 'duplicate', 'external', 'benchmark', 'source', 'policy', 'reserve'])
def test_calendar_economic_and_reserve_boundaries(case):
    snapshot = numeric_snapshot()
    if case == 'gap': del snapshot['development']['curve'][50]
    if case == 'duplicate': snapshot['session_dates'][50] = snapshot['session_dates'][49]
    if case == 'external': snapshot['development']['curve'][100]['cash_eur'] = '1001'
    if case == 'benchmark': snapshot['development']['trades'] = []
    if case == 'source': snapshot['source']['currency'] = 'USD'
    if case == 'policy': snapshot['config']['policy'] = 'other'
    if case == 'reserve': snapshot['protocol']['holdout_date'] = snapshot['session_dates'][-1]
    assert evaluate(snapshot)['status'] == 'no_evaluable'


@pytest.mark.parametrize('n', [503,2001])
def test_work_or_sample_limit_before_random_allocation(n, monkeypatch):
    monkeypatch.setattr(np.random, 'PCG64', lambda *a: pytest.fail('No random allocation for invalid sample'))
    assert evaluate(numeric_snapshot(n))['status'] == 'no_evaluable'


def test_numerical_return_reference_excludes_warmup_and_does_not_recharge_fees():
    snapshot = numeric_snapshot()
    snapshot['development']['curve'][2].update(sma_eur='800', buy_hold_eur='500')
    snapshot['development']['curve'][3].update(sma_eur='1000', buy_hold_eur='600')
    n, _, reasons, _, returns = prepare(snapshot)
    assert n == 504 and reasons == []
    assert list(map(float, returns[0])) == [.25,.2]
    assert list(map(float, returns[1])) == [0., pytest.approx(2/3)]


@pytest.mark.parametrize('change', [dict(acknowledge_exploratory=1), dict(acknowledge_exploratory=False),
    dict(related_protocol_ids=['a'*64,'a'*64]), dict(related_protocol_ids=[]), dict(revision=True),
    dict(revision_hash='wrong'), dict(seed=1), dict(reason='')])
def test_strict_statistical_request(change):
    body = dict(protocol_id='a'*64, candidate_id='b'*64, revision=1, revision_hash='c'*64,
        related_protocol_ids=['a'*64], reason='Consulta exploratoria justificada', acknowledge_exploratory=True)
    with pytest.raises(ValueError): RobustnessInput(**{**body, **change})


def test_separate_storage_no_reserve_or_candidate_writes_and_reproduction(lab, monkeypatch):
    store, lab_service, body = lab
    protocol = lab_service.create(body)
    ident = protocol['protocol']['id']
    request = statistical_request(store, ident)
    before = store.read(lambda w: [tuple(r) for r in w.db.execute('SELECT * FROM records ORDER BY kind,id')])
    original = UnitOfWork.get
    def guarded(work, kind, *args, **kwargs):
        assert kind not in ('lab_protocol', 'candidate_revision')
        return original(work, kind, *args, **kwargs)
    monkeypatch.setattr(UnitOfWork, 'get', guarded)
    service = RobustnessService(store)
    result = service.create(request)
    RobustnessReport.model_validate(result)
    assert result['result']['status'] == 'no_evaluable'
    assert result == service.create(request)
    restarted = RobustnessService(Store(store.path))
    assert restarted.read(result['id']) == result
    assert restarted.reproduce(result['id'])['matches'] is True
    assert restarted.history(request.candidate_id)['items'] == [result]
    after = store.read(lambda w: [tuple(r) for r in w.db.execute("SELECT * FROM records WHERE kind!='robustness_report' ORDER BY kind,id")])
    assert before == after
    saved = store.read(lambda w: w.get('robustness_report', result['id']))['snapshot']['development']
    assert not ({'bars','openings','holdout','frozen'} & saved.keys())
    assert all(d < body.holdout_date for d in saved['session_dates'])
    assert store.read(lambda w: w.db.execute("SELECT count(*) FROM audit WHERE event='lab.robustness_saved'").fetchone()[0]) == 1


def test_context_conflict_and_failed_audit_leave_no_report(lab, monkeypatch):
    store, lab_service, body = lab
    ident = lab_service.create(body)['protocol']['id']
    request = statistical_request(store, ident)
    service = RobustnessService(store)
    original = UnitOfWork.audit
    def fail(work, event, *args, **kwargs):
        if event == 'lab.robustness_saved': raise RuntimeError('audit unavailable')
        return original(work, event, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(UnitOfWork, 'audit', fail)
        with pytest.raises(RuntimeError): service.create(request)
    assert service.history(request.candidate_id)['items'] == []
    original_snapshot = service._snapshot
    calls = 0
    def changed(work, body):
        nonlocal calls
        calls += 1
        result = original_snapshot(work, body)
        if calls == 2: result['revision_hash'] = '0'*64
        return result
    monkeypatch.setattr(service, '_snapshot', changed)
    with pytest.raises(RevisionConflict, match='contexto'): service.create(request)
    assert service.history(request.candidate_id)['items'] == []


def test_cannot_omit_related_trials_or_use_wrong_revision(lab):
    store, lab_service, body = lab
    ident = lab_service.create(body)['protocol']['id']
    request = statistical_request(store, ident)
    other = lab_service.create(body.model_copy(update={'name': 'Otro ensayo relacionado'}))['protocol']['id']
    current = CandidateService(store).read(request.candidate_id)
    revised = CandidateService(store).revise(request.candidate_id, CandidateRevisionInput(
        name=current['name'], hypothesis=current['hypothesis'], reason='También considerar el otro ensayo.',
        protocol_ids=[ident,other], expected_revision=1))
    with pytest.raises(ValueError, match='todos'):
        RobustnessService(store).create(request.model_copy(update=dict(revision=2, revision_hash=revised['revision_hash'])))
    with pytest.raises(RevisionConflict):
        RobustnessService(store).create(request.model_copy(update=dict(revision_hash='0'*64)))
    # An explicitly selected immutable older revision is valid and remains labelled as such.
    assert RobustnessService(store).create(request)['request']['revision'] == 1


def test_http_guards_query_and_reproduce(lab):
    store, service, body = lab
    request = statistical_request(store, service.create(body)['protocol']['id'])
    with TestClient(create_app(store.path.parent, run_worker=False)) as client:
        payload = request.model_dump(mode='json')
        assert client.post('/api/lab/robustness', json=payload).status_code == 403
        response = client.post('/api/lab/robustness', json=payload, headers=LOCAL)
        assert response.status_code == 200, response.text
        report = response.json()
        assert client.get('/api/lab/robustness/'+report['id']).json() == report
        assert len(client.get('/api/lab/robustness', params={'candidate_id':request.candidate_id}).json()['items']) == 1
        assert client.post('/api/lab/robustness/'+report['id']+'/reproduce', json={}, headers=LOCAL).json()['matches']
        assert client.get('/api/lab/robustness', params={'candidate_id':request.candidate_id, 'limit':21}).status_code == 422


@pytest.mark.parametrize('case', ['basis', 'events', 'float_overflow', 'sum_overflow', 'numpy'])
def test_numerical_and_source_rejection_before_bootstrap(case, monkeypatch):
    snapshot = numeric_snapshot()
    if case == 'basis': snapshot['source']['basis_verified'] = False
    if case == 'events': snapshot['source']['corporate_policy'] = 'unknown'
    if case == 'float_overflow': snapshot['development']['curve'][3]['sma_eur'] = '1e1000'
    if case == 'sum_overflow': snapshot['development']['curve'][3]['sma_eur'] = '1e310'
    if case == 'numpy': monkeypatch.setattr(np, '__version__', 'other')
    monkeypatch.setattr(np.random, 'PCG64', lambda *a: pytest.fail('Invalid input must not sample'))
    assert evaluate(snapshot)['status'] == 'no_evaluable'


def test_concurrent_report_is_idempotent_and_shared_capacity_is_released(lab, monkeypatch):
    store, service, body = lab
    request = statistical_request(store, service.create(body)['protocol']['id'])
    service = RobustnessService(store)
    gate = Barrier(2)
    def simultaneous(snapshot):
        gate.wait(timeout=10)
        return evaluate(snapshot)
    monkeypatch.setattr('atlas_quant.robustness_service.evaluate', simultaneous)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: service.create(request), range(2)))
    assert results[0] == results[1]
    assert len(service.history(request.candidate_id)['items']) == 1
    assert store.read(lambda w: w.db.execute("SELECT count(*) FROM audit WHERE event='lab.robustness_saved'").fetchone()[0]) == 1
    with _SLOTS, _SLOTS:
        with pytest.raises(ComputationBusy): service.create(request)
        with pytest.raises(ComputationBusy): service.reproduce(results[0]['id'])
    assert service.create(request) == results[0]


@pytest.mark.parametrize('changed', ['report', 'snapshot'])
def test_reproduction_reports_corruption_without_rewriting(lab, changed):
    store, service, body = lab
    request = statistical_request(store, service.create(body)['protocol']['id'])
    service = RobustnessService(store)
    report = service.create(request)
    value = store.read(lambda w: w.get('robustness_report', report['id']))
    if changed == 'report': value['report']['request']['reason'] = 'Tampered context'
    else: value['snapshot']['development']['development']['curve'][0]['sma_eur'] = '777'
    # Deliberate isolated storage corruption, not an application write path.
    store.atomic(lambda w: w.db.execute("UPDATE records SET body=? WHERE kind='robustness_report' AND id=?",
        (json.dumps(value), report['id'])))
    assert not service.reproduce(report['id'])['matches']
    assert store.read(lambda w: w.get('robustness_report', report['id'])) == value


def test_evaluable_real_service_path_504_intervals(tmp_path):
    store = Store(tmp_path/'atlas.sqlite3')
    catalog = CatalogService(store)
    c = catalog.add('instrument', dict(expected_revision=0, name='Robustez ficticia', source='Escenario sintético'))
    c = catalog.add('listing', dict(expected_revision=c['revision'], instrument_id=c['instruments'][0]['id'], currency='EUR', market='TEST'))
    market, protocol = fixture_request()
    days = [(date(2023, 1, 1)+timedelta(days=i)).isoformat() for i in range(514)]
    prices, sessions, calendar = [], [], []
    for i, day in enumerate(days):
        close = 100 + i%11
        prices.append(f'{day},ASSET,100,{max(100,close)},100,{close},100,EUR,{day}T17:01:00Z')
        sessions.append(f'{day},{day}T09:00:00Z,{day}T17:00:00Z,{day}T09:00:00Z')
        calendar.append(f'{day},open,{day}T17:00:00Z')
    market['csv'] = market['csv'].splitlines()[0]+'\n'+'\n'.join(prices)
    market['evidence']['calendar_csv'] = 'date,status,close_at\n'+'\n'.join(calendar)
    protocol.update(start_date=days[0], holdout_date=days[507], end_date=days[-1],
        sessions_csv='date,open_at,close_at,open_available_at\n'+'\n'.join(sessions))
    request = MarketImport(**market, listing_id=c['listings'][0]['id'])
    service = MarketService(store)
    preview = service.import_series('prices', request)
    series = service.import_series('prices', request.model_copy(update=dict(commit=True, preview_token=preview['preview_token'])))['series']
    body = LabInput(**protocol, series_id=series['id'], series_version=series['version'])
    lab_service = LabService(store)
    development = lab_service.create(body)
    ident = development['protocol']['id']
    service = RobustnessService(store)
    report = service.create(statistical_request(store, ident))
    RobustnessReport.model_validate(report)
    assert report['result']['status'] == 'exploratory', report['result']['reasons']
    assert report['result']['intervals'] == 504
    assert report['metrics'] == development['development']['metrics']
    assert service.reproduce(report['id'])['matches']
    assert lab_service.read(ident) == development and development['holdout'] is None

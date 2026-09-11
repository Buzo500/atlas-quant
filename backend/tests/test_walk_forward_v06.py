"""Temporal isolation, fixed-rule diagnostics and atomic publication invariants."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import localcontext, ROUND_UP
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from atlas_quant.catalog import CatalogService, RevisionConflict
from atlas_quant.lab_contracts import LabInput, LabReport, POLICY
from atlas_quant.lab_service import LabService
from atlas_quant.lab_sources import freeze_source
from atlas_quant.market_contracts import MarketImport
from atlas_quant.market_service import MarketService
from atlas_quant.quality import digest
from atlas_quant.store import Store, UnitOfWork
from atlas_quant.walk_forward import evaluate, plan, _diagnose, _summary
from atlas_quant.walk_forward_contracts import WalkForwardConfig
from test_lab_v06 import fixture_request, lab, open_request  # noqa: F401


def reference_request(count=37, development=30):
    market, body = fixture_request()
    days = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    prices = ['date,listing_ref,open,high,low,close,volume,currency,available_at']
    sessions = ['date,open_at,close_at,open_available_at']
    for i, day in enumerate(days):
        close = [10, 10, 10, 12, 10, 8, 8][i % 7]
        op = 8 if i % 7 == 6 else 10
        prices.append(f'{day},ASSET,{op},{max(op, close)},{min(op, close)},{close},100,EUR,{day}T17:01:00Z')
        sessions.append(f'{day},{day}T09:00:00Z,{day}T17:00:00Z,{day}T09:00:00Z')
    market['name'] = 'Walk-forward ficticio EUR'
    market['csv'] = '\n'.join(prices)
    market['evidence']['calendar_csv'] = 'date,status,close_at\n' + '\n'.join(f'{d},open,{d}T17:00:00Z' for d in days)
    body.update(name='Walk-forward ficticio', start_date=days[0], holdout_date=days[development], end_date=days[-1],
        sessions_csv='\n'.join(sessions), walk_forward=dict(context_sessions=7, evaluation_sessions=7))
    return market, body


@pytest.fixture
def wf(tmp_path):
    store = Store(tmp_path / 'wf.sqlite3')
    catalog = CatalogService(store)
    c = catalog.add('instrument', dict(expected_revision=0, name='WF ficticio', source='Fixture sintético'))
    c = catalog.add('listing', dict(expected_revision=c['revision'], instrument_id=c['instruments'][0]['id'], currency='EUR', market='TEST'))
    market, body = reference_request()
    request = MarketImport(**market, listing_id=c['listings'][0]['id'])
    service = MarketService(store)
    preview = service.import_series('prices', request)
    series = service.import_series('prices', request.model_copy(update=dict(commit=True, preview_token=preview['preview_token'])))['series']
    body = LabInput(**body, series_id=series['id'], series_version=series['version'])
    service = LabService(store)
    frozen = freeze_source(*store.read(lambda w: service._snapshot(w, body)), body)
    return store, service, body, frozen


def test_old_protocol_identity_and_payload_unchanged(lab):
    store, service, body = lab
    frozen = freeze_source(*store.read(lambda w: service._snapshot(w, body)), body)
    old_inputs = body.model_dump(mode='json', exclude={'walk_forward', 'sensitivity'})
    expected = digest(dict(policy=POLICY, inputs=old_inputs, frozen=frozen))
    result = service.create(body)
    assert result['protocol']['id'] == expected
    assert 'walk_forward' not in result
    assert store.read(lambda w: w.get('lab_protocol', expected))['inputs'] == old_inputs


def test_windows_nonoverlap_reset_capital_tail_and_reproduction(wf):
    store, service, body, frozen = wf
    result = service.create(body)
    LabReport.model_validate(result)
    report = result['walk_forward']
    assert len(report['windows']) == 3
    assert [(w['evaluation']['start_date'], w['evaluation']['end_date']) for w in report['windows']] == [
        ('2025-01-08', '2025-01-14'), ('2025-01-15', '2025-01-21'), ('2025-01-22', '2025-01-28')]
    assert (report['unused_sessions'], report['unused_start'], report['unused_end']) == (2, '2025-01-29', '2025-01-30')
    assert [w['warmup_start'] for w in report['windows']] == ['2025-01-05', '2025-01-12', '2025-01-19']
    # Same seven-session cycle, independent cash: all windows have identical metrics.
    assert all(w['evaluation']['metrics'] == report['windows'][0]['evaluation']['metrics'] for w in report['windows'])
    # 99 units bought at 10 + 1 fee, then sold at 8 - 1: 800. Buy/hold retains 99 * 8 + 9 cash.
    assert [m['final_nav_eur'] for m in report['windows'][0]['evaluation']['metrics']] == ['800', '801', '1000']
    assert report['summary']['mean_return_pct'] == '-20'
    assert report['summary']['mean_excess_pct'] == '-0.1'
    assert all(p['cash_eur'] == '1000' for w in report['windows'] for p in w['evaluation']['curve'])
    assert result['holdout'] is None and not result['protocol']['opened']
    ident = result['protocol']['id']
    assert service.create(body) == result
    assert LabService(Store(store.path)).read(ident) == result
    assert service.reproduce(ident) == dict(id=ident, development_matches=True, holdout_matches=None, walk_forward_matches=True)
    assert store.read(lambda w: w.db.execute("SELECT COUNT(*) FROM audit WHERE event='lab.development_saved'").fetchone()[0]) == 1
    assert service.open_holdout(ident, open_request(ident))['walk_forward'] == report
    assert service.reproduce(ident)['walk_forward_matches'] is True


def test_holdout_prices_and_openings_never_read(wf):
    _, _, body, frozen = wf
    expected = evaluate(frozen, body)
    class Protected(dict):
        def __getitem__(self, key):
            assert key < body.holdout_date, 'Final-test value read'
            return super().__getitem__(key)
        def get(self, key, default=None):
            assert key < body.holdout_date, 'Final-test value read'
            return super().get(key, default)
        def items(self):
            raise AssertionError('Do not enumerate final-test values')
    frozen['bars'] = Protected(frozen['bars'])
    frozen['openings'] = Protected(frozen['openings'])
    assert evaluate(frozen, body) == expected


def test_future_development_cannot_change_an_earlier_window(wf):
    _, _, body, frozen = wf
    expected = evaluate(frozen, body)['windows'][0]
    changed = deepcopy(frozen)
    for day, bar in changed['bars'].items():
        if day > expected['evaluation']['end_date']:
            bar.update(open='500', high='500', low='500', close='500')
    assert evaluate(changed, body)['windows'][0] == expected


@pytest.mark.parametrize('change', ['warmup_gap', 'evaluation_gap', 'missing_open', 'late_open'])
def test_missing_data_not_silently_counted_as_pass(wf, change):
    _, _, body, frozen = wf
    if change.endswith('gap'):
        frozen['bars'].pop('2025-01-06' if change == 'warmup_gap' else '2025-01-10')
    else:
        frozen['openings']['2025-01-08'] = None if change == 'missing_open' else '2025-01-08T09:01:00Z'
    report = evaluate(frozen, body)
    assert not report['windows'][0]['evaluable'] and not report['windows'][0]['passed']
    assert report['summary']['status'] == 'insufficient_data'
    assert report['summary']['evaluable_windows'] < 3


@pytest.mark.parametrize('development,config,message', [
    (8, dict(context_sessions=7, evaluation_sessions=7), 'dos ventanas'),
    (100, dict(context_sessions=5, evaluation_sessions=2), '20 ventanas'),
    (2000, dict(context_sessions=1000, evaluation_sessions=50), '20.000'),
])
def test_bounds_fail_before_calculation(development, config, message):
    sessions = [dict(date=f'{i:04}') for i in range(development)]
    body = LabInput(**reference_request()[1], series_id='s', series_version=1).model_copy(update=dict(
        holdout_date='9999', walk_forward=WalkForwardConfig(**config)))
    with pytest.raises(ValueError, match=message):
        plan(sessions, body)


def test_context_cannot_be_shorter_than_sma(wf):
    _, _, body, frozen = wf
    with pytest.raises(ValueError, match='media lenta'):
        plan(frozen['calendar']['sessions'], body.model_copy(update=dict(slow=6)))


@pytest.mark.parametrize('changes', [dict(minimum_pass_pct='100.0001'), dict(maximum_drawdown_pct='-1'),
    dict(minimum_pass_pct='NaN'), dict(context_sessions=True), dict(evaluation_sessions=2.5), dict(unknown=1)])
def test_strict_threshold_contract(changes):
    with pytest.raises(ValueError):
        WalkForwardConfig(**changes)


def test_threshold_equality_passes_and_one_small_excess_fails():
    config = WalkForwardConfig(minimum_windows=2, minimum_pass_pct='50', maximum_drawdown_pct='15')
    metrics = [dict(return_pct='0', max_drawdown_pct='15', fills=1), dict(return_pct='0', max_drawdown_pct='0', fills=1), {}]
    result = dict(metrics=metrics)
    assert _diagnose(result, True, config) == (True, True, [])
    good = dict(evaluable=True, passed=True, evaluation=result)
    bad = dict(evaluable=True, passed=False, evaluation=result)
    assert _summary([good, bad], config)['status'] == 'meets_criteria'
    assert _summary([good, bad], config.model_copy(update=dict(minimum_pass_pct='50.0001')))['status'] == 'does_not_meet'
    metrics[0]['max_drawdown_pct'] = '15.0001'
    assert _diagnose(result, True, config)[1] is False
    metrics[0].update(max_drawdown_pct='15', fills=0)
    assert _diagnose(result, True, config)[1] is False
    metrics[0].update(fills=1, return_pct='-0.0001')
    assert _diagnose(result, True, config)[1] is False


def test_minimum_windows_is_diagnostic_not_silent_truncation(wf):
    _, _, body, frozen = wf
    body = body.model_copy(update=dict(walk_forward=WalkForwardConfig(context_sessions=7, evaluation_sessions=10)))
    report = evaluate(frozen, body)
    assert report['summary']['windows'] == 2
    assert report['summary']['status'] == 'insufficient_data'


def test_decimal_context_cannot_change_results(wf):
    _, _, body, frozen = wf
    expected = evaluate(frozen, body)
    with localcontext() as context:
        context.prec, context.rounding = 6, ROUND_UP
        assert evaluate(frozen, body) == expected


def test_atomic_rollback_includes_walk_forward_and_reservation(wf, monkeypatch):
    store, service, body, frozen = wf
    original = UnitOfWork.audit
    def fail(work, event, *args, **kwargs):
        if event == 'lab.development_saved':
            raise RuntimeError('audit unavailable')
        return original(work, event, *args, **kwargs)
    monkeypatch.setattr(UnitOfWork, 'audit', fail)
    with pytest.raises(RuntimeError, match='audit unavailable'):
        service.create(body)
    assert service.history()['items'] == []
    assert store.read(lambda w: w.lab_overlaps('lab_reservation', frozen['source']['instrument_id'], body.start_date, body.end_date)) is False


def test_final_reservation_guard_still_applies(wf):
    _, service, body, _ = wf
    first = service.create(body)
    service.open_holdout(first['protocol']['id'], open_request(first['protocol']['id']))
    changed = body.model_copy(update=dict(walk_forward=WalkForwardConfig(context_sessions=7, evaluation_sessions=7, minimum_pass_pct='70')))
    with pytest.raises(RevisionConflict):
        service.create(changed)


def test_concurrent_publication_has_one_report_and_audit(wf, monkeypatch):
    store, service, body, _ = wf
    import atlas_quant.lab_service as module
    original = module.walk_forward
    barrier = Barrier(2)
    def synchronized(*args):
        result = original(*args)
        barrier.wait(timeout=10)
        return result
    monkeypatch.setattr(module, 'walk_forward', synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: service.create(body), range(2)))
    assert results[0] == results[1]
    assert len(service.history()['items']) == 1
    assert store.read(lambda w: w.db.execute("SELECT COUNT(*) FROM audit WHERE event='lab.development_saved'").fetchone()[0]) == 1


def test_evidence_change_during_walk_forward_does_not_publish(wf, monkeypatch):
    store, service, body, _ = wf
    import atlas_quant.lab_service as module
    original = module.walk_forward
    def changed(*args):
        result = original(*args)
        prior = UnitOfWork.corporate_state
        monkeypatch.setattr(UnitOfWork, 'corporate_state', lambda work: dict(prior(work), revision=999))
        return result
    monkeypatch.setattr(module, 'walk_forward', changed)
    with pytest.raises(RevisionConflict, match='evidencia'):
        service.create(body)
    assert service.history()['items'] == []

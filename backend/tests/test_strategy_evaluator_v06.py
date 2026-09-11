"""Numerical references and temporal/recovery invariants of the new evaluator."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import localcontext
from fractions import Fraction
import json
import random

import pytest
from pydantic import ValidationError

from atlas_quant.quality import digest
from atlas_quant.strategy_spec import CloseObservation, OpeningObservation, SmaSpec
from atlas_quant.strategy_evaluator import (
    dump_checkpoint, evaluate, initial_state, load_checkpoint, opening_eligibility, replay,
)


def spec_document(count=160, fast=20, slow=50):
    days = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(count)]
    # Explicit synthetic calendar: every day is a fixture session, not an
    # inferred calendar or evidence for real market data.
    return dict(strategy_id='fixture-sma', revision=1, fast=fast, slow=slow,
        source=dict(kind='synthetic', id='fixture-prices', version=1, sha256='a'*64,
            instrument_id='FIXTURE', listing_id='FIXTURE.EUR', market='XTEST',
            basis_verified=True, evidence_sha256='b'*64),
        calendar=dict(id='fixture-calendar', version=1, market='XTEST', timezone='UTC',
            source='Synthetic test fixture, not exchange evidence', verified=True,
            sessions=[dict(date=day, open_at=day+'T09:00:00Z', close_at=day+'T17:00:00Z') for day in days]))


def make_spec(**kwargs):
    return SmaSpec.model_validate_json(json.dumps(spec_document(**kwargs)))


def observation(spec, index, close='100', **kwargs):
    session = spec.calendar.sessions[index]
    payload = dict(spec_hash=spec.fingerprint, session_index=index, close=close,
        available_at=session.date+'T17:01:00Z', decision_at=session.date+'T17:02:00Z')
    payload.update(kwargs)
    if payload.get('status', 'observed') != 'observed':
        payload.update(close=None, available_at=None)
    return CloseObservation(**payload)


def events(spec, prices):
    return [observation(spec, i, str(price)) for i, price in enumerate(prices)]


def signals(results):
    return [(r.intent.session_index, r.intent.target_weight) for r in results if r.intent]


def test_twenty_fifty_reference_first_cross_equality_and_exit():
    spec = make_spec()
    result = replay(spec, events(spec, [100]*50 + [110, 90, 80]))
    assert all(r.status == 'warming' and r.intent is None for r in result[:50])
    assert signals(result) == [(50, 1), (52, 0)]
    assert result[51].state.target_weight == 1 and result[51].intent is None
    assert result[50].intent.target_basis == 'strategy-budget'
    assert result[50].intent.next_open_at == spec.calendar.sessions[51].open_at
    assert result[50].intent.status == 'pending'


def test_initial_above_is_not_a_cross_and_flat_does_not_emit_sell():
    spec = make_spec()
    assert signals(replay(spec, events(spec, range(1, 130)))) == []
    assert signals(replay(spec, events(spec, [100]*50 + [90]))) == []


def test_small_independent_reference():
    spec = make_spec(fast=2, slow=3)
    assert signals(replay(spec, events(spec, [10, 10, 10, 12, 10, 8]))) == [(3, 1), (5, 0)]


@pytest.mark.parametrize('fast,slow', [(2, 3), (20, 50), (49, 50), (50, 100)])
def test_replay_matches_fraction_oracle_and_incremental_checkpoint(fast, slow):
    spec = make_spec(count=350, fast=fast, slow=slow)
    rng = random.Random(927)
    prices = [str(rng.randrange(90000, 110000)/100) for _ in range(330)]
    expected, target = [], 0
    numbers = list(map(Fraction, prices))
    for i in range(slow, len(numbers)):
        previous = sum(numbers[i-fast:i])/fast - sum(numbers[i-slow:i])/slow
        current = sum(numbers[i-fast+1:i+1])/fast - sum(numbers[i-slow+1:i+1])/slow
        desired = 1 if previous <= 0 < current else 0 if previous >= 0 > current else target
        if desired != target:
            expected.append((i, desired))
        target = desired
    observations = events(spec, prices)
    batch = replay(spec, observations)
    state = initial_state(spec)
    incremental = []
    for event in observations:
        step = evaluate(spec, state, event)
        incremental.append(step)
        state = load_checkpoint(spec, dump_checkpoint(step.state))
    assert signals(batch) == expected
    assert tuple(incremental) == batch
    assert len({r.intent.key for r in batch if r.intent}) == len(expected)


def test_precision_independent_of_global_decimal_context():
    spec = make_spec(fast=2, slow=3)
    rows = events(spec, ['999999999999.123456789012']*3 + ['999999999999.123456789013'])
    with localcontext() as context:
        context.prec = 2
        low = replay(spec, rows)
    with localcontext() as context:
        context.prec = 80
        high = replay(spec, rows)
    assert low == high
    assert signals(high) == [(3, 1)]


def test_pure_inputs_and_canonical_json_roundtrip():
    spec = make_spec(fast=2, slow=3)
    other = SmaSpec.model_validate_json(spec.model_dump_json())
    assert spec.fingerprint == other.fingerprint
    initial = initial_state(spec)
    event = observation(spec, 0, '100.0000')
    saved = (initial.model_dump_json(), event.model_dump_json(), spec.model_dump_json())
    result = evaluate(spec, initial, event)
    assert result.state.closes == ('100',)
    assert saved == (initial.model_dump_json(), event.model_dump_json(), spec.model_dump_json())


@pytest.mark.parametrize('status', ['missing', 'unverified'])
def test_gap_preserves_target_and_restarts_full_warmup(status):
    spec = make_spec(fast=2, slow=3)
    initial = replay(spec, events(spec, [10, 10, 10, 12]))[-1].state
    blocked = evaluate(spec, initial, observation(spec, 4, status=status))
    assert blocked.status == 'blocked' and blocked.state.target_weight == 1
    assert blocked.state.closes == () and blocked.intent is None
    tail = replay(spec, [observation(spec, i, p) for i, p in enumerate(['10','10','10','9'], 5)], blocked.state)
    assert all(r.intent is None for r in tail[:3])
    assert signals(tail) == [(8, 0)]


def test_skipped_declared_session_is_detected_without_synthetic_exit():
    spec = make_spec(fast=2, slow=3)
    state = replay(spec, events(spec, [10, 10, 10, 12]))[-1].state
    result = evaluate(spec, state, observation(spec, 5, '8'))
    assert result.reasons == ('missing_session',)
    assert result.status == 'blocked' and result.intent is None
    assert result.state.closes == ('8',) and result.state.target_weight == 1


def test_corporate_action_requires_new_source_and_replay_not_just_warmup():
    spec = make_spec(fast=2, slow=3)
    state = replay(spec, events(spec, [10, 10, 10, 12]))[-1].state
    blocked = evaluate(spec, state, observation(spec, 4, status='corporate_action'))
    result = replay(spec, [observation(spec, i, '8') for i in range(5, 12)], blocked.state)
    assert all(r.status == 'blocked' and not r.intent and not r.state.closes for r in result)
    assert all(r.state.target_weight == 1 and r.state.halted_reason == 'corporate_action' for r in result)


def test_no_future_close_used_and_waiting_can_be_retried():
    spec = make_spec(fast=2, slow=3)
    state = replay(spec, events(spec, [10, 10, 10]))[-1].state
    day = spec.calendar.sessions[3].date
    for price in ['12', '900']:
        early = evaluate(spec, state, observation(spec, 3, price, decision_at=day+'T16:00:00Z'))
        unavailable = evaluate(spec, state, observation(spec, 3, price, decision_at=day+'T17:00:00Z'))
        assert early.state == unavailable.state == state
        assert early.intent is unavailable.intent is None
    assert evaluate(spec, state, observation(spec, 3, '12')).intent.target_weight == 1


def test_changing_future_observation_cannot_change_past_decisions():
    spec = make_spec(fast=2, slow=3)
    original = replay(spec, events(spec, [10, 10, 10, 12, 10, 8]))
    revised = replay(spec, events(spec, [10, 10, 10, 12, 100, 200]))
    assert original[:4] == revised[:4]


def test_retry_does_not_duplicate_intent_and_corrections_conflict():
    spec = make_spec(fast=2, slow=3)
    rows = events(spec, [10, 10, 10, 12])
    state = replay(spec, rows)[-1].state
    repeat = evaluate(spec, load_checkpoint(spec, dump_checkpoint(state)), rows[-1])
    assert repeat.status == 'duplicate' and repeat.intent is None and repeat.state == state
    with pytest.raises(ValueError, match='otro contenido'):
        evaluate(spec, state, observation(spec, 3, '13'))
    with pytest.raises(ValueError, match='fuera de orden'):
        evaluate(spec, state, rows[0])


@pytest.mark.parametrize('delay', ['09:00:00', '10:00:00'])
def test_decision_at_or_after_next_open_is_expired(delay):
    spec = make_spec(fast=2, slow=3)
    state = replay(spec, events(spec, [10, 10, 10]))[-1].state
    next_day = spec.calendar.sessions[4].date
    row = observation(spec, 3, '12', available_at=next_day+'T'+delay+'Z', decision_at=next_day+'T'+delay+'Z')
    intent = evaluate(spec, state, row).intent
    assert intent.status == 'expired' and intent.expiry_reason == 'decision_not_before_next_open'


def test_unknown_next_session_expires_and_clock_cannot_reverse():
    spec = make_spec(count=4, fast=2, slow=3)
    result = replay(spec, events(spec, [10,10,10,12]))
    assert result[-1].intent.expiry_reason == 'next_session_unknown'
    with pytest.raises(ValueError, match='retroceder'):
        evaluate(spec, result[2].state, observation(spec, 3, decision_at=spec.calendar.sessions[0].close_at))


def test_opening_guard_does_not_use_future_prices_or_allow_late_fill():
    spec = make_spec(fast=2, slow=3)
    intent = replay(spec, events(spec, [10, 10, 10, 12]))[-1].intent
    day = spec.calendar.sessions[4].date
    def opening(**kwargs):
        payload = dict(spec_hash=spec.fingerprint, open_at=intent.next_open_at,
                       decision_at=intent.next_open_at, price='13', available_at=intent.next_open_at)
        payload.update(kwargs)
        return OpeningObservation(**payload)
    assert opening_eligibility(intent, opening()) == 'eligible'
    for price in ['13','900']:
        assert opening_eligibility(intent, opening(price=price, decision_at=day+'T08:00:00Z')) == 'waiting_for_open'
    assert opening_eligibility(intent, opening(price=None, available_at=None)) == 'opening_price_missing'
    assert opening_eligibility(intent, opening(available_at=day+'T09:01:00Z')) == 'opening_price_late'
    assert opening_eligibility(intent, opening(decision_at=day+'T09:01:00Z')) == 'opening_opportunity_expired'
    with pytest.raises(ValueError, match='siguiente apertura'):
        opening_eligibility(intent, opening(open_at=day+'T08:00:00Z'))


def test_checkpoint_corruption_and_binding_are_rejected():
    spec = make_spec(fast=2, slow=3)
    state = replay(spec, events(spec, [10,10,10,12]))[-1].state
    saved = dump_checkpoint(state)
    payload = json.loads(saved)
    payload['state']['target_weight'] = 0
    with pytest.raises(ValueError, match='corrupto'):
        load_checkpoint(spec, json.dumps(payload))
    changed = spec_document(fast=2, slow=3)
    changed['source']['version'] = 2
    other = SmaSpec.model_validate_json(json.dumps(changed))
    with pytest.raises(ValueError, match='otra especificación'):
        load_checkpoint(other, saved)
    with pytest.raises(ValueError, match='esta especificación'):
        evaluate(spec, initial_state(spec), observation(other, 0))
    payload['state']['closes'] = ['10']*4
    payload['sha256'] = digest(payload['state'])
    with pytest.raises(ValueError, match='excede'):
        load_checkpoint(spec, json.dumps(payload))


@pytest.mark.parametrize('change', [
    {'strategy': 'python'}, {'expression': '__import__("os")'}, {'fast': True},
    {'fast': 20.0}, {'fast': '20'}, {'fast': 1}, {'slow': 251}, {'fast': 50, 'slow': 50},
])
def test_invalid_or_executable_spec_rejected(change):
    document = spec_document()
    document.update(change)
    with pytest.raises(ValidationError):
        SmaSpec.model_validate_json(json.dumps(document))


@pytest.mark.parametrize('price', ['0', '-1', 'nan', 'Infinity', '1e3', '01', '1.1234567890123', 12.0, True])
def test_invalid_prices_rejected(price):
    with pytest.raises(ValidationError):
        observation(make_spec(), 0, price)


@pytest.mark.parametrize('which', ['unverified', 'basis', 'currency', 'market', 'duplicate', 'overlap', 'timezone', 'date'])
def test_invalid_evidence_calendar_or_currency_rejected(which):
    document = spec_document()
    if which == 'unverified': document['calendar']['verified'] = 1
    if which == 'basis': document['source']['basis_verified'] = False
    if which == 'currency': document['source']['currency'] = 'USD'
    if which == 'market': document['source']['market'] = 'OTHER'
    if which == 'duplicate': document['calendar']['sessions'][1] = deepcopy(document['calendar']['sessions'][0])
    if which == 'overlap': document['calendar']['sessions'][1]['open_at'] = document['calendar']['sessions'][0]['open_at']
    if which == 'timezone': document['calendar']['timezone'] = 'Invalid/Zone'
    if which == 'date': document['calendar']['sessions'][0]['date'] = '2026-01-02'
    with pytest.raises(ValidationError):
        SmaSpec.model_validate_json(json.dumps(document))


def test_reference_tool_exports_reproducible_synthetic_evidence():
    from run_sma_reference import run_reference
    report = run_reference()
    assert report == run_reference()
    assert report['replay_incremental_parity'] is True
    assert [(item['session_index'], item['target_weight']) for item in report['intents']] == [(50, 1), (52, 0)]
    assert report['ordinary_data_touched'] is report['execution_implemented'] is False
    assert report['synthetic'] is True


def test_invalid_availability_and_missing_observation_shape():
    spec = make_spec()
    with pytest.raises(ValueError, match='anterior al cierre'):
        evaluate(spec, initial_state(spec), observation(spec, 0, available_at=spec.calendar.sessions[0].open_at))
    with pytest.raises(ValidationError, match='precio y disponibilidad'):
        observation(spec, 0, available_at=None)
    with pytest.raises(ValidationError):
        observation(spec, 0, available_at='2026-01-01T17:01:00')


def test_retry_with_a_later_clock_still_has_no_second_effect():
    spec = make_spec(fast=2, slow=3)
    prior = replay(spec, events(spec, [10, 10, 10, 12]))[-1].state
    repeated = evaluate(spec, prior, observation(spec, 3, '12', decision_at=spec.calendar.sessions[4].open_at))
    assert repeated.status == 'duplicate' and repeated.intent is None and repeated.state == prior


@pytest.mark.parametrize('change', ['parameters', 'calendar', 'source', 'evidence'])
def test_frozen_context_changes_invalidate_checkpoint(change):
    original = make_spec()
    saved = dump_checkpoint(replay(original, events(original, [100]*50 + [110]))[-1].state)
    document = spec_document()
    if change == 'parameters': document['fast'] = 19
    if change == 'calendar': document['calendar']['sessions'][-1]['close_at'] = document['calendar']['sessions'][-1]['date']+'T16:00:00Z'
    if change == 'source': document['source']['sha256'] = 'c'*64
    if change == 'evidence': document['source']['evidence_sha256'] = 'c'*64
    other = SmaSpec.model_validate_json(json.dumps(document))
    assert original.fingerprint != other.fingerprint
    with pytest.raises(ValueError, match='otra especificación'):
        load_checkpoint(other, saved)

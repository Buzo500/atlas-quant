"""One pure transition shared by replay and future incremental research.

This emits desired exposure, never fills, orders or actual positions. Legacy
backtest semantics remain versioned and untouched until an explicit migration.
"""
from __future__ import annotations

import json
from collections.abc import Iterable

from .quality import digest, timestamp
from .strategy_spec import (
    CloseObservation, EvaluationResult, OpeningObservation, SmaSpec,
    StrategyState, TargetIntent, price_units,
)


def initial_state(spec: SmaSpec) -> StrategyState:
    return StrategyState(spec_hash=spec.fingerprint, prefix_hash=digest({'initial': spec.fingerprint}))


def _check_state(spec: SmaSpec, state: StrategyState):
    if state.spec_hash != spec.fingerprint:
        raise ValueError('El checkpoint pertenece a otra especificación, datos o calendario.')
    if state.last_index >= len(spec.calendar.sessions) or len(state.closes) > spec.slow:
        raise ValueError('El checkpoint excede el calendario o calentamiento de la especificación.')
    if state.last_index == -1 and state != initial_state(spec):
        raise ValueError('Huella inicial incoherente.')


def _relation(closes: tuple[str, ...], fast: int, slow: int) -> int:
    values = tuple(price_units(value) for value in closes)
    delta = sum(values[-fast:]) * slow - sum(values[-slow:]) * fast
    return (delta > 0) - (delta < 0)


def evaluate(spec: SmaSpec, state: StrategyState, observation: CloseObservation) -> EvaluationResult:
    """Consume one declared session using only information available at decision_at.

    A retry of the last identical observation emits nothing. An older event or a
    correction conflicts: the caller must replay from a prior checkpoint on the
    appropriate frozen version, never overwrite a historical decision in place.
    """
    _check_state(spec, state)
    if observation.spec_hash != spec.fingerprint:
        raise ValueError('La observación no pertenece a esta especificación y versión de fuentes.')
    index = observation.session_index
    if index >= len(spec.calendar.sessions):
        raise ValueError('La sesión no figura en el calendario congelado.')
    observation_hash = digest(observation.model_dump(mode='json', exclude={'decision_at'}))
    if index < state.last_index:
        raise ValueError('Observación fuera de orden; requiere replay explícito.')
    if index == state.last_index:
        if observation_hash != state.last_observation_hash:
            raise ValueError('La sesión ya consumida tiene otro contenido; requiere nueva versión y replay.')
        return EvaluationResult(state=state, status='duplicate')
    decision = timestamp(observation.decision_at)
    if state.last_decision_at and decision < timestamp(state.last_decision_at):
        raise ValueError('El reloj de decisión no puede retroceder.')
    session = spec.calendar.sessions[index]
    if decision < timestamp(session.close_at):
        return EvaluationResult(state=state, status='waiting', reasons=('session_not_closed',))
    if observation.status == 'observed':
        available = timestamp(observation.available_at)
        if available < timestamp(session.close_at):
            raise ValueError('Disponibilidad de cierre anterior al cierre declarado.')
        if available > decision:
            return EvaluationResult(state=state, status='waiting', reasons=('close_not_available',))

    reasons = []
    window = state.closes
    if index != state.last_index + 1:
        reasons.append('missing_session')
        window = ()
    target, intent = state.target_weight, None
    status = 'warming'
    halted = state.halted_reason or ('corporate_action' if observation.status == 'corporate_action' else None)
    if observation.status != 'observed' or halted:
        reasons.append(halted or observation.status)
        window, status = (), 'blocked'
    else:
        # Integer cross-multiplication gives exact comparisons even at equality.
        current = (*window, observation.close)
        if len(window) == spec.slow:
            before = _relation(window, spec.fast, spec.slow)
            after = _relation(current, spec.fast, spec.slow)
            crossed = 'cross_up' if before <= 0 < after else 'cross_down' if before >= 0 > after else None
            status = 'evaluated'
            desired = 1 if crossed == 'cross_up' else 0
            if crossed and desired != target:
                target = desired
                next_open = spec.calendar.sessions[index + 1].open_at if index + 1 < len(spec.calendar.sessions) else None
                expiry = 'next_session_unknown' if next_open is None else (
                    'decision_not_before_next_open' if decision >= timestamp(next_open) else None)
                intent = TargetIntent(
                    key=digest({'spec': spec.fingerprint, 'prior': state.prefix_hash,
                                'observation': observation_hash, 'decision': observation.decision_at,
                                'target': target}),
                    spec_hash=spec.fingerprint, strategy_id=spec.strategy_id,
                    instrument_id=spec.source.instrument_id, listing_id=spec.source.listing_id,
                    session_index=index, session_date=session.date, decision_at=observation.decision_at,
                    target_weight=target, reason=crossed, next_open_at=next_open,
                    status='expired' if expiry else 'pending', expiry_reason=expiry,
                )
        window = current[-spec.slow:]
        if reasons:
            status = 'blocked'
    updated = StrategyState(
        spec_hash=spec.fingerprint, last_index=index, last_observation_hash=observation_hash,
        last_decision_at=observation.decision_at, closes=window, target_weight=target,
        halted_reason=halted,
        prefix_hash=digest({'prior': state.prefix_hash, 'observation': observation_hash,
                            'decision': observation.decision_at}),
    )
    return EvaluationResult(state=updated, status=status, reasons=tuple(reasons), intent=intent)


def replay(spec: SmaSpec, observations: Iterable[CloseObservation],
           state: StrategyState | None = None) -> tuple[EvaluationResult, ...]:
    """Bound a replay; incremental callers invoke exactly the same transition."""
    current = state if state is not None else initial_state(spec)
    results = []
    for observation in observations:
        if len(results) >= 100_000:
            raise ValueError('Máximo 100.000 observaciones por replay.')
        result = evaluate(spec, current, observation)
        results.append(result)
        current = result.state
    return tuple(results)


def opening_eligibility(intent: TargetIntent, observation: OpeningObservation) -> str:
    """Temporal guard only: eligible is NOT a fill, risk approval or dedup commit.

    The future execution coordinator must atomically consume intent.key exactly
    once with risk and economic validation. This pure function has no effects.
    """
    if observation.spec_hash != intent.spec_hash:
        raise ValueError('La apertura pertenece a otra especificación.')
    if intent.status == 'expired':
        return intent.expiry_reason
    if observation.open_at != intent.next_open_at:
        raise ValueError('Solo se admite la siguiente apertura declarada.')
    if timestamp(observation.decision_at) < timestamp(observation.open_at):
        return 'waiting_for_open'
    if timestamp(observation.decision_at) > timestamp(observation.open_at):
        return 'opening_opportunity_expired'
    if observation.price is None:
        return 'opening_price_missing'
    if timestamp(observation.available_at) > timestamp(observation.open_at):
        return 'opening_price_late'
    return 'eligible'


def dump_checkpoint(state: StrategyState) -> str:
    payload = state.model_dump(mode='json')
    return json.dumps({'state': payload, 'sha256': digest(payload)}, sort_keys=True, separators=(',', ':'))


def load_checkpoint(spec: SmaSpec, document: str) -> StrategyState:
    """Validate a local checkpoint; checksum detects corruption, not authenticity."""
    if len(document) > 50_000:
        raise ValueError('Checkpoint demasiado grande.')
    envelope = json.loads(document)
    if not isinstance(envelope, dict) or set(envelope) != {'state', 'sha256'}:
        raise ValueError('Formato de checkpoint desconocido.')
    if digest(envelope['state']) != envelope['sha256']:
        raise ValueError('Checkpoint corrupto.')
    state = StrategyState.model_validate_json(json.dumps(envelope['state']))
    _check_state(spec, state)
    return state

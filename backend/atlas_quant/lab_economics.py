"""Period replay and benchmarks using the same fill policy and NativeBook.

The SMA account is cold-started in each partition. Benchmarks deliberately have
no SMA warm-up: they measure the opportunity cost of that strategy choice.
"""
from dataclasses import dataclass
from decimal import Decimal as D, localcontext, ROUND_HALF_EVEN
import json

from .book import NativeBook, decimal_text as text
from .quality import digest, timestamp
from .strategy_spec import SmaSpec, CloseObservation, OpeningObservation
from .strategy_simulation import SmaSimulation, _entry, _execute, _valuation


@dataclass(frozen=True)
class BenchmarkTarget:
    key: str
    target_weight: int = 1


def metric(name, values, fills, capital):
    peak, drawdown = capital, D(0)
    complete = all(v is not None for v in values)
    for v in values:
        if v is not None:
            peak = max(peak, D(v))
            drawdown = max(drawdown, (peak-D(v))/peak*100)
    final = values[-1]
    return dict(name=name, final_nav_eur=final,
        return_pct=text((D(final)/capital-1)*100) if final is not None else None,
        max_drawdown_pct=text(drawdown) if complete else None, fills=len(fills),
        fees_eur=text(sum((D(f['fee_eur']) for f in fills), D(0)), money=True))


def period(frozen, body, holdout):
    sessions = [s for s in frozen['calendar']['sessions'] if (s['date'] >= body.holdout_date) == holdout]
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        return _period(frozen, body, sessions)


def window_period(frozen, body, start, end, *, warmup=0):
    """Half-open session indices; warm-up is a preceding prefix, never a fill."""
    sessions = frozen['calendar']['sessions']
    if not 0 <= start < end <= len(sessions) or not 0 <= warmup <= min(body.slow, start):
        raise ValueError('Rango de evaluación o calentamiento no válido.')
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        return _period(frozen, body, sessions[start:end], sessions[start-warmup:start])


def _close(frozen, spec, index, session):
    bar = frozen['bars'].get(session.date)
    return CloseObservation(spec_hash=spec.fingerprint, session_index=index,
        status='observed' if bar else 'missing', close=bar['close'] if bar else None,
        available_at=bar['available_at'] if bar else None,
        decision_at=bar['available_at'] if bar else session.close_at)


def _period(frozen, body, sessions, warmup_sessions=()):
    calendar = dict(frozen['calendar'])
    calendar['sessions'] = [*warmup_sessions, *sessions]
    spec = SmaSpec.model_validate_json(json.dumps(dict(strategy_id='lab-sma', revision=1, fast=body.fast,
        slow=body.slow, source=frozen['source'], calendar=calendar)))
    config = body.config
    prefix = len(warmup_sessions)
    warmup = tuple(_close(frozen, spec, i, s) for i, s in enumerate(spec.calendar.sessions[:prefix]))
    simulation = SmaSimulation(spec, config, warmup=warmup)
    baseline = NativeBook()
    first = spec.calendar.sessions[prefix]
    baseline.apply(_entry(first.date, 0, 'deposit', D(config.initial_cash_eur)))
    benchmark_target = BenchmarkTarget(digest(dict(policy='buy-hold-first-open-v1', spec=spec.fingerprint, config=config.fingerprint)))
    curve, trades, baseline_fills = [], [], []
    rejected, expired = 0, 0
    for i, session in enumerate(spec.calendar.sessions[prefix:], start=prefix):
        bar = frozen['bars'].get(session.date)
        available = frozen['openings'][session.date]
        opening = OpeningObservation(spec_hash=spec.fingerprint, open_at=session.open_at, decision_at=session.open_at,
            price=bar['open'] if bar and available else None, available_at=available if bar else None)
        simulation.process(opening)
        if i == prefix and opening.price and timestamp(available) == timestamp(session.open_at):
            baseline, outcome, _ = _execute(baseline, spec, config, benchmark_target, opening, session.date)
            if outcome['fill']:
                baseline_fills.append(outcome['fill'])
                trades.append(dict(strategy='Comprar y mantener', side='buy', **{k: outcome['fill'][k]
                    for k in ('date', 'quantity', 'price_eur', 'fee_eur')}))
            rejected += outcome['status'] == 'rejected'
        elif i == prefix:
            expired += 1
        close = _close(frozen, spec, i, session)
        record = simulation.process(close)
        valuation = _valuation(baseline, session.date, spec.source.listing_id, D(bar['close']) if bar else None, config)
        curve.append(dict(date=session.date, sma_eur=record['nav_eur'], buy_hold_eur=valuation['nav_eur'], cash_eur=config.initial_cash_eur))
    report = simulation.report()
    sma_fills = []
    for outcome in report['executions']:
        if outcome['fill']:
            sma_fills.append(outcome['fill'])
            trades.append(dict(strategy='SMA', side=outcome['side'], **{k: outcome['fill'][k]
                for k in ('date', 'quantity', 'price_eur', 'fee_eur')}))
        rejected += outcome['status'] == 'rejected'
        expired += outcome['status'] == 'expired'
    capital = D(config.initial_cash_eur)
    result = dict(start_date=first.date, end_date=spec.calendar.sessions[-1].date, sessions=len(curve),
        metrics=[metric('SMA', [r['sma_eur'] for r in curve], sma_fills, capital),
                 metric('Comprar y mantener', [r['buy_hold_eur'] for r in curve], baseline_fills, capital),
                 metric('Efectivo', [r['cash_eur'] for r in curve], [], capital)],
        curve=curve, trades=sorted(trades, key=lambda t: t['date']), rejected=rejected, expired=expired)
    return dict(**result, report_hash=digest(dict(policy='lab-warmed-period-eur-v1' if prefix else 'lab-period-eur-v1', spec=spec.fingerprint,
        config=config.fingerprint, result=result, journal=report['journal'])))

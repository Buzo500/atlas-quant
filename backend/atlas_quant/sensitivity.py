"""OAT replay on development only; optional scenarios cannot touch the holdout."""
from decimal import Decimal as D, localcontext, ROUND_HALF_EVEN, ROUND_CEILING
from .book import decimal_text as text
from .lab_economics import period
from .quality import digest, timestamp
from .simulation_contracts import SimulationConfig
from .sensitivity_contracts import SENSITIVITY_POLICY
from .walk_forward import plan as walk_plan


def plan(body, sessions):
    config = body.sensitivity
    if config is None:
        raise ValueError('El protocolo no tiene sensibilidad declarada.')
    count = sum(s['date'] < body.holdout_date for s in sessions)
    cases = [('base', body)]
    for axis, values in (('fast', config.fast_windows), ('slow', config.slow_windows)):
        for value in values:
            if value == getattr(body, axis):
                continue
            variant = body.model_copy(update={axis: value})
            if variant.fast >= variant.slow or count < variant.slow + 2:
                raise ValueError('Cada variante necesita rápida < lenta y desarrollo de al menos lenta + 2 sesiones.')
            cases.append((f'{axis}:{value}', variant))
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        for factor in config.cost_multipliers:
            costs = body.config.model_dump(mode='json')
            for field in ('fixed_fee_eur', 'fee_bps', 'slippage_bps'):
                value = D(costs[field]) * D(factor)
                costs[field] = text(value.quantize(D('.01'), rounding=ROUND_CEILING) if field == 'fixed_fee_eur' else value)
            updated = SimulationConfig.model_validate(costs)
            if updated == body.config or any(v.config == updated for _, v in cases):
                continue
            cases.append((f'cost:{factor}', body.model_copy(update=dict(config=updated))))
    if not 2 <= len(cases) <= 8:
        raise ValueError('Declara entre dos y ocho casos económicos distintos, incluida la base.')
    work = len(cases) * count
    if body.walk_forward is not None:
        wf = body.walk_forward
        work += len(walk_plan(sessions, body)) * (wf.context_sessions + wf.evaluation_sessions + body.slow)
    if len(cases) * count > 24_000 or work > 30_000:
        raise ValueError('La combinación supera el límite de 30.000 sesiones procesadas. Reduce variantes o ventanas.')
    return cases


def evaluate(frozen, body, development):
    sessions = [s for s in frozen['calendar']['sessions'] if s['date'] < body.holdout_date]
    source = dict(frozen, calendar=dict(frozen['calendar'], sessions=sessions),
        bars={s['date']: frozen['bars'][s['date']] for s in sessions if s['date'] in frozen['bars']},
        openings={s['date']: frozen['openings'][s['date']] for s in sessions})
    complete = all(s['date'] in source['bars'] and source['openings'][s['date']] is not None and
        timestamp(source['openings'][s['date']]) == timestamp(s['open_at']) for s in sessions)
    cases = []
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        for label, variant in plan(body, frozen['calendar']['sessions']):
            result = development if label == 'base' else period(source, variant, False)
            metrics = result['metrics'][0]
            evaluable = complete and metrics['return_pct'] is not None and metrics['max_drawdown_pct'] is not None
            reasons = [] if evaluable else ['Faltan precios o disponibilidad de apertura; no se interpreta como resultado válido.']
            cases.append(dict(label=label, fast=variant.fast, slow=variant.slow,
                config=variant.config.model_dump(mode='json'), result=result, evaluable=evaluable, reasons=reasons))
        valid = [c['result']['metrics'][0] for c in cases if c['evaluable']]
        returns = [D(m['return_pct']) for m in valid]
        summary = dict(cases=len(cases), evaluable_cases=len(valid),
            min_return_pct=text(min(returns)) if returns else None, max_return_pct=text(max(returns)) if returns else None,
            return_spread_pp=text(max(returns)-min(returns)) if returns else None,
            worst_drawdown_pct=text(max(D(m['max_drawdown_pct']) for m in valid)) if valid else None,
            nonnegative_cases=sum(value >= 0 for value in returns),
            reasons=[] if len(valid) == len(cases) else ['Hay casos no evaluables. La dispersión solo resume los casos evaluables.'])
        report = dict(policy=SENSITIVITY_POLICY, config=body.sensitivity.model_dump(mode='json'), cases=cases, summary=summary,
            warnings=['Variaciones de un factor cada vez sobre desarrollo. No mide interacciones ni significación estadística.',
                'Cuentas independientes con calentamiento dentro del periodo. No se calcula la prueba final ni el walk-forward de las variantes.',
                'No selecciona ganadores ni modifica parámetros, candidatas, carteras u órdenes.'])
        return dict(report, report_hash=digest(report))

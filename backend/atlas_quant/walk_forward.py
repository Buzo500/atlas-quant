"""Bounded, fixed-rule temporal evaluation confined to development sessions."""
from decimal import Decimal as D, localcontext, ROUND_HALF_EVEN

from .book import decimal_text as text
from .lab_economics import window_period
from .quality import digest, timestamp
from .walk_forward_contracts import WF_POLICY


def plan(sessions, body):
    config = body.walk_forward
    if config is None:
        raise ValueError('El protocolo no tiene configuración walk-forward.')
    count = sum(s['date'] < body.holdout_date for s in sessions)
    context, evaluation = config.context_sessions, config.evaluation_sessions
    if context < body.slow + 2:
        raise ValueError('El contexto walk-forward necesita al menos media lenta + 2 sesiones.')
    windows = max(0, (count - context) // evaluation)
    if windows < 2:
        raise ValueError('Walk-forward necesita al menos dos ventanas completas dentro del desarrollo.')
    if windows > 20 or windows * (context + evaluation + body.slow) > 20_000:
        raise ValueError('Walk-forward supera 20 ventanas o 20.000 sesiones procesadas; acota el periodo o amplía la evaluación.')
    return [(i * evaluation, i * evaluation + context, (i + 1) * evaluation + context)
            for i in range(windows)]


def _diagnose(result, complete, config):
    sma, benchmark, _ = result['metrics']
    evaluable = complete and all(m[k] is not None for m in (sma, benchmark)
                                for k in ('return_pct', 'max_drawdown_pct'))
    reasons = []
    if not evaluable:
        reasons.append('Faltan cierres o aperturas disponibles al abrir en el calentamiento o la evaluación.')
    if sma['fills'] < config.minimum_fills:
        reasons.append(f"Menos de {config.minimum_fills} ejecuciones SMA.")
    if evaluable:
        if D(sma['return_pct']) < 0:
            reasons.append('Rentabilidad SMA neta negativa.')
        if D(sma['return_pct']) < D(benchmark['return_pct']):
            reasons.append('La SMA queda por debajo de comprar y mantener.')
        if D(sma['max_drawdown_pct']) > D(config.maximum_drawdown_pct):
            reasons.append('La caída máxima supera el límite declarado.')
    return evaluable, evaluable and not reasons, reasons


def _summary(windows, config):
    valid = [w for w in windows if w['evaluable']]
    passing = sum(w['passed'] for w in windows)
    fraction = D(passing) / len(windows) * 100
    reasons = []
    insufficient = len(windows) < config.minimum_windows or len(valid) != len(windows)
    if len(windows) < config.minimum_windows:
        reasons.append(f'Se requieren al menos {config.minimum_windows} ventanas completas.')
    if len(valid) != len(windows):
        reasons.append('Hay ventanas con evidencia insuficiente; no se excluyen para aprobar el conjunto.')
    if fraction < D(config.minimum_pass_pct):
        reasons.append('La proporción de ventanas que cumplen queda por debajo del mínimo declarado.')
    metrics = [w['evaluation']['metrics'] for w in valid]
    return dict(status='insufficient_data' if insufficient else 'does_not_meet' if reasons else 'meets_criteria',
        windows=len(windows), evaluable_windows=len(valid), passing_windows=passing, passing_pct=text(fraction),
        mean_return_pct=text(sum((D(m[0]['return_pct']) for m in metrics), D(0)) / len(metrics)) if metrics else None,
        mean_excess_pct=text(sum((D(m[0]['return_pct']) - D(m[1]['return_pct']) for m in metrics), D(0)) / len(metrics)) if metrics else None,
        worst_drawdown_pct=text(max(D(m[0]['max_drawdown_pct']) for m in metrics)) if metrics else None,
        reasons=reasons)


def evaluate(frozen, body):
    bounds = plan(frozen['calendar']['sessions'], body)
    # Build a view by date lookup: final-test prices are never read here.
    sessions = [s for s in frozen['calendar']['sessions'] if s['date'] < body.holdout_date]
    development = dict(frozen, calendar=dict(frozen['calendar'], sessions=sessions),
        bars={s['date']: frozen['bars'][s['date']] for s in sessions if s['date'] in frozen['bars']},
        openings={s['date']: frozen['openings'][s['date']] for s in sessions})
    windows = []
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        for index, (start, split, end) in enumerate(bounds, start=1):
            reference = window_period(development, body, start, split)
            result = window_period(development, body, split, end, warmup=body.slow)
            warmup = sessions[split-body.slow:split]
            complete = all(s['date'] in development['bars'] for s in warmup + sessions[split:end])
            complete = complete and all(development['openings'][s['date']] is not None and
                timestamp(development['openings'][s['date']]) == timestamp(s['open_at']) for s in sessions[split:end])
            evaluable, passed, reasons = _diagnose(result, complete, body.walk_forward)
            windows.append(dict(index=index, context_start=sessions[start]['date'], context_end=sessions[split-1]['date'],
                warmup_start=warmup[0]['date'], warmup_sessions=body.slow, context_metrics=reference['metrics'],
                context_hash=reference['report_hash'], evaluation=result, evaluable=evaluable, passed=passed, reasons=reasons))
        unused = sessions[bounds[-1][2]:]
        report = dict(policy=WF_POLICY, config=body.walk_forward.model_dump(mode='json'), windows=windows,
            summary=_summary(windows, body.walk_forward), unused_sessions=len(unused),
            unused_start=unused[0]['date'] if unused else None, unused_end=unused[-1]['date'] if unused else None,
            warnings=[
                'Validación retrospectiva dentro del desarrollo; sus datos pueden haber sido vistos. La prueba final sigue reservada.',
                'Parámetros fijos: el contexto es una referencia histórica, no un ajuste ni una selección de parámetros.',
                'Cada evaluación empieza en efectivo. Las medias usan cierres previos; se exige un nuevo cruce dentro de la evaluación.',
                'Las medias aritméticas usan solo ventanas evaluables; no son una rentabilidad compuesta ni una cartera continua.',
                'Cumplir estos criterios no demuestra robustez estadística ni autoriza órdenes. Faltan sensibilidad y pruebas de sobreajuste.',
            ])
        return dict(report, report_hash=digest(report))

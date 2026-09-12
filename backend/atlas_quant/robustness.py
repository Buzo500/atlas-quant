"""Paired stationary bootstrap. Receives development NAV, never market/holdout data."""
from decimal import Decimal as D, localcontext, ROUND_HALF_EVEN, InvalidOperation
import hashlib
import numpy as np
from .quality import digest
from .robustness_contracts import POLICY

NUMPY_VERSION = '2.5.2'
MASTER_SEED = 20260911
LENGTHS = (5, 10, 20)
REPLICAS = 5000
MIN_INTERVALS, MAX_INTERVALS, MAX_WORK = 504, 2000, 30_000_000
WARNINGS = [
    'Intervalo exploratorio condicionado al histórico; no predice rentabilidad futura ni autoriza operaciones.',
    'El bootstrap requiere estacionariedad y dependencia débil; este informe no acredita esas hipótesis.',
    '95 % es el nivel nominal del intervalo; la cobertura real puede ser inferior con muestras finitas o dependencia persistente.',
    'Sin ajuste por selección o multiplicidad. Los ensayos declarados no acreditan experimentos realizados fuera de ATLAS.',
    'Exceso aritmético diario SMA menos comprar/mantener, sin anualizar ni interpretar réplicas como probabilidad de éxito.',
    'Solo desarrollo de una cuenta; no mezcla reinicios walk-forward ni utiliza la prueba final.',
    'Costes ya incluidos en el NAV. Los límites de exposición configurados no son una medición de exposición realizada.',
]


def pp(value):
    with localcontext() as ctx:
        value = D(str(float(value)))
        ctx.prec, ctx.rounding = max(64, value.adjusted()+16), ROUND_HALF_EVEN
        return format((value * 100).quantize(D('0.000000000001')), 'f')


def seed_for(development_hash, length):
    return int(digest(dict(policy=POLICY, seed=MASTER_SEED, L=length,
                           development_hash=development_hash))[:32], 16)


def indices_from_draws(starts, restarts):
    """Deterministic, vectorized circular runs; used by the independent oracle tests."""
    n = len(starts)
    positions = np.arange(n, dtype=np.int64)
    last = np.maximum.accumulate(np.where(np.r_[True, restarts], positions, 0))
    return (starts[last] + positions - last) % n


def stationary_means(pairs, length, seed, replicas=REPLICAS):
    n = len(pairs)
    generator = np.random.Generator(np.random.PCG64(seed))
    means = np.empty(replicas, dtype=np.float64)
    fingerprint = hashlib.sha256()
    for replica in range(replicas):
        starts = generator.integers(0, n, size=n, dtype=np.int64)
        restarts = generator.random(n-1) < 1/length
        indices = indices_from_draws(starts, restarts)
        fingerprint.update(indices.astype('<u4').tobytes())
        sampled = pairs[indices]
        means[replica] = np.mean(sampled[:, 0] - sampled[:, 1], dtype=np.float64)
    return means, fingerprint.hexdigest()


def prepare(snapshot):
    """Check the full post-warmup calendar; never drop missing observations."""
    protocol, development = snapshot['protocol'], snapshot['development']
    curve, dates = development['curve'], snapshot['session_dates']
    slow = protocol['slow']
    n = max(0, len(dates)-slow)
    work = len(LENGTHS) * REPLICAS * n
    reasons = []
    if n < MIN_INTERVALS or any(n/L < 25 for L in LENGTHS):
        reasons.append('Se requieren al menos 504 intervalos completos después del calentamiento y 25 bloques esperados por longitud.')
    if n > MAX_INTERVALS or work > MAX_WORK:
        reasons.append('El informe supera 2.000 intervalos o 30 millones de índices; no se recorta la muestra automáticamente.')
    if not dates or dates != sorted(set(dates)) or any(d >= protocol['holdout_date'] for d in dates):
        reasons.append('El calendario de desarrollo no es válido o invade la prueba final.')
    if [p['date'] for p in curve] != dates or development['sessions'] != len(dates):
        reasons.append('La curva no contiene todas las sesiones consecutivas del calendario de desarrollo.')
    if not any(t['strategy'] == 'Comprar y mantener' and t['side'] == 'buy' and
               t['date'] == protocol['start_date'] for t in development['trades']):
        reasons.append('El benchmark comprar/mantener no entró en la primera apertura del desarrollo.')
    source = snapshot['source']
    if (snapshot['config']['policy'] != 'sma-economics-eur-v1' or source['currency'] != 'EUR'
        or source.get('price_basis') != 'raw' or source.get('basis_verified') is not True
        or source.get('corporate_policy') != 'verified-event-free-v1'):
        reasons.append('Fuente o política económica incompatible con este análisis EUR.')
    if np.__version__ != NUMPY_VERSION:
        reasons.append(f'La política requiere NumPy {NUMPY_VERSION}; no se sustituye el generador silenciosamente.')
    selected = curve[max(0, slow-1):]
    nav_hash = digest(selected)
    if reasons:
        return n, work, reasons, nav_hash, None
    returns = []
    try:
        with localcontext() as ctx:
            ctx.prec, ctx.rounding = 64, ROUND_HALF_EVEN
            for point in selected:
                values = [D(point[k]) for k in ('sma_eur', 'buy_hold_eur', 'cash_eur')]
                if any(not v.is_finite() or v <= 0 for v in values):
                    raise ValueError()
                if values[2] != D(snapshot['config']['initial_cash_eur']):
                    raise ValueError()
            for previous, current in zip(selected, selected[1:]):
                returns.append([str(D(current[k])/D(previous[k])-1) for k in ('sma_eur', 'buy_hold_eur')])
    except (InvalidOperation, TypeError, ValueError, ArithmeticError):
        reasons.append('Hay NAV ausente, no positivo/no finito o capital externo en el tramo, incluido su cierre previo.')
        return n, work, reasons, nav_hash, None
    pairs = np.asarray(returns, dtype=np.float64)
    with np.errstate(over='ignore', invalid='ignore'):
        excess = pairs[:, 0]-pairs[:, 1]
        bounded_sum = np.max(np.abs(excess))*n
    if pairs.shape != (n, 2) or not np.isfinite(pairs).all() or not np.isfinite(bounded_sum):
        reasons.append('Los retornos no son pares float64 completos y finitos.')
        returns = None
    return n, work, reasons, nav_hash, returns


def evaluate(snapshot):
    n, work, reasons, nav_hash, returns = prepare(snapshot)
    result = dict(policy=POLICY, status='no_evaluable' if reasons else 'exploratory', reasons=reasons,
        warnings=WARNINGS, intervals=n, warmup_sessions=snapshot['protocol']['slow'],
        start_date=None, end_date=None, work_indices=work, mean_excess_pp=None,
        principal_includes_zero=None, direction_changes=None, lengths=[], nav_hash=nav_hash,
        returns_hash=None, float_returns_hash=None, prng='PCG64', numpy_version=np.__version__, master_seed=MASTER_SEED)
    if not reasons:
        pairs = np.asarray(returns, dtype=np.float64)
        result.update(start_date=snapshot['session_dates'][snapshot['protocol']['slow']],
            end_date=snapshot['session_dates'][-1], returns_hash=digest(returns),
            float_returns_hash=hashlib.sha256(pairs.astype('<f8').tobytes()).hexdigest(),
            mean_excess_pp=pp(np.mean(pairs[:, 0]-pairs[:, 1], dtype=np.float64)))
        for length in LENGTHS:
            seed = seed_for(snapshot['development']['report_hash'], length)
            means, indices_hash = stationary_means(pairs, length, seed)
            low, high = (pp(q) for q in np.quantile(means, [0.025, 0.975], method='linear'))
            direction = 'positive' if D(low) > 0 else 'negative' if D(high) < 0 else 'uncertain'
            result['lengths'].append(dict(length=length, principal=length == 10, seed=str(seed),
                replicas=REPLICAS, lower_pp=low, upper_pp=high, direction=direction, indices_hash=indices_hash))
        result['principal_includes_zero'] = result['lengths'][1]['direction'] == 'uncertain'
        result['direction_changes'] = len({v['direction'] for v in result['lengths']}) > 1
    return dict(**result, result_hash=digest(result))

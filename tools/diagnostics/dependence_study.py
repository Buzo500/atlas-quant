"""Fixed dependence study v1. Offline diagnostics; never modifies product policy."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import numpy as np
from atlas_quant.quality import digest
from atlas_quant.robustness import NUMPY_VERSION, stationary_means
from robustness_coverage import wilson

POLICY, SEED = 'atlas-dependence-study-v1', 20260914
SIZES, LENGTHS, HISTORIES, REPLICAS = (504, 1008), (10, 20, 40), 500, 5000
DGPS = ('iid_normal', 'ar1_0.6', 'ar1_0.9', 'ar1_0.95', 'iid_student5', 'mean_break')
Z = 1.959963984540054


def seed(dgp, n, history, length=None):
    return int(digest(dict(seed=SEED, dgp=dgp, n=n, history=history, length=length))[:32], 16)


def sample(dgp, n, history):
    rng = np.random.Generator(np.random.PCG64(seed(dgp, n, history)))
    if dgp == 'iid_student5':
        return rng.standard_t(5, n) * .01 * math.sqrt(3 / 5)
    noise = rng.normal(0, .01, n)
    values = noise.copy()
    if dgp.startswith('ar1_'):
        phi = float(dgp.split('_')[1])
        for i in range(1, n):
            values[i] = phi * values[i - 1] + math.sqrt(1 - phi**2) * noise[i]
    elif dgp == 'mean_break':
        values += np.r_[np.full(n // 2, -.005), np.full(n - n // 2, .005)]
    elif dgp != 'iid_normal':
        raise ValueError('Unknown DGP')
    return values


def mean_variance(n, phi, sigma=.01):
    if n < 1 or not -1 < phi < 1:
        raise ValueError('Invalid stationary AR1')
    return sigma**2 / n**2 * (n + 2 * sum((n - k) * phi**k for k in range(1, n)))


def block_histogram(n, length, case_seed, replicas=100):
    # The exact draw order of the product, including unused candidate starts.
    rng = np.random.Generator(np.random.PCG64(case_seed))
    histogram = Counter()
    for _ in range(replicas):
        rng.integers(0, n, size=n, dtype=np.int64)
        cuts = np.r_[0, np.flatnonzero(rng.random(n - 1) < 1 / length) + 1, n]
        histogram.update(int(v) for v in np.diff(cuts))
    return {str(k): v for k, v in sorted(histogram.items())}


def interval(method, low, high, **details):
    return dict(method=method, lower=float(low), upper=float(high), covers=bool(low <= 0 <= high),
                misses_above=bool(low > 0), misses_below=bool(high < 0), **details)


def one_case(case, replicas=REPLICAS):
    dgp, n, history = case
    values = sample(dgp, n, history)
    pairs = np.c_[values, np.zeros(n)]
    observed = float(np.mean(values))
    source = dict(dgp=dgp, n=n, history=history, seed=str(seed(dgp, n, history)), returns=values.tolist())
    rows = []
    for length in LENGTHS:
        case_seed = seed(dgp, n, history, length)
        means, fingerprint = stationary_means(pairs, length, case_seed, replicas=replicas)
        low, high = np.quantile(means, [.025, .975], method='linear')
        rows.append(interval(f'L{length}', low, high, length=length, seed=str(case_seed),
            replicas=replicas, indices_hash=fingerprint, bootstrap_mean_bias=float(np.mean(means) - observed),
            expected_blocks=n / length, product_blocks_admissible=n / length >= 25,
            block_histogram=block_histogram(n, length, case_seed) if history == 0 else None))
    if dgp == 'iid_normal' or dgp.startswith('ar1_'):
        phi = 0. if dgp == 'iid_normal' else float(dgp.split('_')[1])
        half = Z * math.sqrt(mean_variance(n, phi))
        rows.append(interval('oracle', observed - half, observed + half, true_phi=phi))
    return dict(source=source, source_hash=digest(source), sample_mean=observed, methods=rows)


def summarize(cases):
    summary, paired = [], []
    for dgp, n in itertools.product(DGPS, SIZES):
        cell = [r for r in cases if r['dgp'] == dgp and r['n'] == n]
        if len(cell) != HISTORIES or {r['history'] for r in cell} != set(range(HISTORIES)):
            raise ValueError('Incomplete or duplicated histories')
        methods = [r['method'] for r in cell[0]['methods']]
        for method in methods:
            rows = [next(r for r in case['methods'] if r['method'] == method) for case in cell]
            hits = sum(r['covers'] for r in rows)
            bounds = wilson(hits, len(rows))
            widths = np.array([r['upper'] - r['lower'] for r in rows]) * 100
            summary.append(dict(dgp=dgp, n=n, method=method, stationary=dgp != 'mean_break',
                histories=len(rows), covered=hits, coverage=hits / len(rows), wilson_95=bounds,
                mean_width_pp=float(widths.mean()), width_pp_quantiles=np.quantile(widths, [0, .25, .5, .75, 1]).tolist(),
                sample_mean_bias_pp=float(np.mean([r['sample_mean'] for r in cell]) * 100),
                bootstrap_mean_bias_pp=None if method == 'oracle' else float(np.mean([r['bootstrap_mean_bias'] for r in rows]) * 100),
                misses_above=sum(r['misses_above'] for r in rows), misses_below=sum(r['misses_below'] for r in rows)))
        for a, b in itertools.combinations(methods, 2):
            counts = Counter()
            for case in cell:
                hit = {r['method']: r['covers'] for r in case['methods']}
                counts[f'{int(hit[a])}{int(hit[b])}'] += 1
            paired.append(dict(dgp=dgp, n=n, a=a, b=b,
                counts={key: counts[key] for key in ('00', '01', '10', '11')}))
    gates = []
    for length in LENGTHS:
        cells = [r for r in summary if r['method'] == f'L{length}' and (r['dgp'] == 'iid_normal' or r['dgp'].startswith('ar1_'))]
        failures = [dict(dgp=r['dgp'], n=r['n'], coverage=r['coverage'], wilson_upper=r['wilson_95'][1])
                    for r in cells if r['coverage'] < .92 or r['wilson_95'][1] < .95]
        gates.append(dict(method=f'L{length}', diagnostic_filter_passed=not failures,
                          failed_cells=failures, product_promotion=False))
    return dict(summary=summary, paired=paired, gates=gates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workers', type=int, default=6, choices=range(1, 9))
    args = parser.parse_args()
    if np.__version__ != NUMPY_VERSION:
        raise ValueError(f'Requires NumPy {NUMPY_VERSION}')
    args.output.mkdir(parents=True, exist_ok=False)
    names = ('tools/diagnostics/dependence_study.py', 'tools/diagnostics/robustness_coverage.py',
             'backend/atlas_quant/robustness.py', 'backend/atlas_quant/quality.py',
             'docs/v0_6_dependencia_revision.md', 'docs/v0_6_dev8_plan.md')
    plan = dict(policy=POLICY, seed=SEED, sizes=SIZES, dgps=DGPS, lengths=LENGTHS, histories=HISTORIES,
        replicas=REPLICAS, quantile='linear', target=0, numpy=np.__version__, python=platform.python_version(),
        workers=args.workers, block_audit_histories=[0], block_audit_replicas=100,
        code_sha256={name: hashlib.sha256((ROOT / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for name in names})
    (args.output / 'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    started = time.monotonic()
    cases = []
    jobs = itertools.product(DGPS, SIZES, range(HISTORIES))
    with (args.output / 'histories.jsonl').open('x', encoding='utf-8') as trace, \
         (args.output / 'cases.jsonl').open('x', encoding='utf-8') as output, \
         ProcessPoolExecutor(max_workers=args.workers) as executor:
        for result in executor.map(one_case, jobs, chunksize=5):
            source = result.pop('source')
            trace.write(json.dumps(source, allow_nan=False) + '\n')
            row = dict(dgp=source['dgp'], n=source['n'], history=source['history'], **result)
            output.write(json.dumps(row, allow_nan=False) + '\n')
            cases.append(row)
            if len(cases) % 50 == 0:
                trace.flush(); output.flush()
                print(json.dumps(dict(completed=len(cases), total=6000, seconds=round(time.monotonic()-started, 1))), flush=True)
    result = dict(plan=plan, plan_hash=digest(plan), **summarize(cases), seconds=time.monotonic()-started,
                  histories_sha256=hashlib.sha256((args.output/'histories.jsonl').read_bytes()).hexdigest(),
                  cases_sha256=hashlib.sha256((args.output/'cases.jsonl').read_bytes()).hexdigest())
    result['result_hash'] = digest(result)
    (args.output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(dict(complete=True, result_hash=result['result_hash'], seconds=result['seconds'], gates=result['gates'])), flush=True)


if __name__ == '__main__':
    main()

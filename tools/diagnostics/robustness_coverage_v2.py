"""Predeclared expanded coverage study. Offline; never tunes the product method."""
import argparse
import hashlib
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
from atlas_quant.robustness import LENGTHS, NUMPY_VERSION, REPLICAS, seed_for, stationary_means
from robustness_coverage import wilson

POLICY = 'atlas-robustness-coverage-v2'
N, HISTORIES, SEED = 504, 100, 20260913
SCENARIOS = ('iid_normal', 'ar1_0.6', 'ar1_0.9', 'iid_student5', 'variance_break', 'mean_break')


def sample(generator, scenario):
    noise = generator.normal(0., .01, N)
    if scenario.startswith('ar1_'):
        phi = float(scenario.split('_')[1])
        values = noise.copy()
        for i in range(1, N):
            values[i] = phi * values[i-1] + math.sqrt(1-phi**2) * noise[i]
        return values
    if scenario == 'iid_student5':
        return generator.standard_t(5, N) * .01 * math.sqrt(3/5)
    if scenario == 'variance_break':
        noise[N//2:] *= 2
    if scenario == 'mean_break':
        noise += np.r_[np.full(N//2, -.005), np.full(N-N//2, .005)]
    return noise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if np.__version__ != NUMPY_VERSION:
        raise ValueError(f'Requires NumPy {NUMPY_VERSION}')
    args.output.mkdir(parents=True, exist_ok=False)
    code = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        'tools/diagnostics/robustness_coverage_v2.py', 'tools/diagnostics/robustness_coverage.py',
        'backend/atlas_quant/robustness.py', 'backend/atlas_quant/quality.py')}
    plan = dict(policy=POLICY, scenarios=SCENARIOS, histories=HISTORIES, intervals=N, seed=SEED,
                lengths=LENGTHS, principal=10, replicas=REPLICAS, quantile='linear',
                target=0, code_sha256=code, numpy=np.__version__, python=platform.python_version())
    (args.output/'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    rows = []
    started = time.monotonic()
    with (args.output/'histories.jsonl').open('x', encoding='utf-8') as trace:
        for index, scenario in enumerate(SCENARIOS):
            for history in range(HISTORIES):
                generator = np.random.Generator(np.random.PCG64(np.random.SeedSequence([SEED, index, history])))
                values = sample(generator, scenario)
                source = dict(scenario=scenario, history=history, returns=values.tolist())
                source_hash = digest(source)
                trace.write(json.dumps(source, allow_nan=False)+'\n')
                trace.flush()
                for length in LENGTHS:
                    seed = seed_for(source_hash, length)
                    means, fingerprint = stationary_means(np.c_[values, np.zeros(N)], length, seed)
                    low, high = np.quantile(means, [.025, .975], method='linear')
                    rows.append(dict(scenario=scenario, history=history, length=length,
                        lower=float(low), upper=float(high), covers=bool(low <= 0 <= high),
                        false_positive=bool(low > 0), false_negative=bool(high < 0),
                        seed=str(seed), source_hash=source_hash, indices_hash=fingerprint))
                if (history+1) % 10 == 0:
                    print(f'{scenario}: {history+1}/{HISTORIES}', flush=True)
    summary = []
    for scenario in SCENARIOS:
        for length in LENGTHS:
            group = [r for r in rows if r['scenario'] == scenario and r['length'] == length]
            count = sum(r['covers'] for r in group)
            summary.append(dict(scenario=scenario, stationary=not scenario.endswith('break'),
                length=length, covered=count, histories=HISTORIES, coverage=count/HISTORIES,
                wilson_95=wilson(count, HISTORIES), misses_above=sum(r['false_positive'] for r in group),
                misses_below=sum(r['false_negative'] for r in group),
                mean_width_pp=float(np.mean([r['upper']-r['lower'] for r in group])*100)))
    result = dict(plan=plan, plan_hash=digest(plan), summary=summary, rows=rows,
                  seconds=time.monotonic()-started, platform=platform.platform())
    result['result_hash'] = digest(result)
    (args.output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(dict(summary=summary, seconds=result['seconds'])), flush=True)


if __name__ == '__main__':
    main()

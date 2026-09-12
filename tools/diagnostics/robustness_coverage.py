"""Predeclared Monte Carlo experiment, offline and separate from product tests.

See docs/v0_6_robustez_implementacion.md. This experiment does not certify nominal
coverage for a market series or tune the method after looking at its results.
"""
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

HISTORIES, N, SEED = 60, 504, 20260912


def wilson(successes, count):
    z, p = 1.959963984540054, successes/count
    denominator = 1+z*z/count
    center = (p+z*z/(2*count))/denominator
    half = z*math.sqrt(p*(1-p)/count+z*z/(4*count*count))/denominator
    return [center-half, center+half]


def main():
    if np.__version__ != NUMPY_VERSION:
        raise RuntimeError(f'Requires NumPy {NUMPY_VERSION}')
    started = time.monotonic()
    rows = []
    for scenario_index, scenario in enumerate(('iid', 'ar1_phi_0.6', 'mean_change')):
        generator = np.random.Generator(np.random.PCG64(np.random.SeedSequence([SEED, scenario_index])))
        for history in range(HISTORIES):
            noise = generator.normal(0., .01, N)
            values = noise.copy()
            if scenario == 'ar1_phi_0.6':
                # Stationary initialization: the first draw has marginal sigma .01.
                for i in range(1, N):
                    values[i] = .6*values[i-1] + math.sqrt(1-.6**2)*noise[i]
            if scenario == 'mean_change':
                values += np.r_[np.full(N//2, -.005), np.full(N-N//2, .005)]
            pairs = np.c_[values, np.zeros(N)]
            source_hash = digest(dict(scenario=scenario, history=history, returns=values.tolist()))
            for length in LENGTHS:
                means, index_hash = stationary_means(pairs, length, seed_for(source_hash, length))
                low, high = np.quantile(means, [.025, .975], method='linear')
                rows.append(dict(scenario=scenario, history=history, length=length, low=float(low),
                    high=float(high), covers=bool(low <= 0 <= high), indices_hash=index_hash, source_hash=source_hash))
            if (history+1) % 10 == 0:
                print(f'{scenario}: {history+1}/{HISTORIES}', flush=True)
    summary = []
    for scenario in ('iid', 'ar1_phi_0.6', 'mean_change'):
        for length in LENGTHS:
            group = [r for r in rows if r['scenario'] == scenario and r['length'] == length]
            count = sum(r['covers'] for r in group)
            summary.append(dict(scenario=scenario, length=length, covered=count, histories=HISTORIES,
                coverage=count/HISTORIES, monte_carlo_wilson_95=wilson(count, HISTORIES),
                mean_width_pp=float(np.mean([r['high']-r['low'] for r in group])*100)))
    result = dict(policy='atlas-robustness-coverage-v1', seed=SEED, histories=HISTORIES, intervals=N,
        replicas=REPLICAS, numpy=np.__version__, python=platform.python_version(), platform=platform.platform(),
        rows=rows, summary=summary)
    result['result_hash'] = digest(result)
    output = ROOT / 'output/validation/robustness-coverage.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(summary=summary, result_hash=result['result_hash'], seconds=time.monotonic()-started)))


if __name__ == '__main__':
    main()

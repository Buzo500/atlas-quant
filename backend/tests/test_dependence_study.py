from pathlib import Path
import sys

import numpy as np
import pytest

DIAGNOSTICS = Path(__file__).resolve().parents[2] / 'tools/diagnostics'
sys.path.insert(0, str(DIAGNOSTICS))
import dependence_study as study


@pytest.mark.parametrize('phi', [0, .6, .9, .95, -.5])
def test_oracle_matches_covariance_sum(phi):
    n = 8
    matrix = .01**2 * phi**np.abs(np.arange(n)[:, None] - np.arange(n))
    assert study.mean_variance(n, phi) == pytest.approx(matrix.sum()/n**2, rel=1e-13)


def test_independent_seeds_and_stationary_initialization():
    assert len({study.seed('iid_normal', n, h, l) for n in study.SIZES for h in range(5)
                for l in (None, *study.LENGTHS)}) == 40
    for dgp in study.DGPS:
        assert np.array_equal(study.sample(dgp, 504, 0), study.sample(dgp, 504, 0))
    rng = np.random.Generator(np.random.PCG64(study.seed('ar1_0.9', 504, 0)))
    noise = rng.normal(0, .01, 504)
    observed = study.sample('ar1_0.9', 504, 0)
    assert observed[0] == noise[0]
    assert observed[1] == .9*noise[0] + np.sqrt(1-.9**2)*noise[1]


def test_block_histogram_conserves_drawn_observations():
    counts = study.block_histogram(8, 10, 42)
    assert sum(int(k)*v for k,v in counts.items()) == 800
    assert all(1 <= int(k) <= 8 for k in counts)


def test_interval_tails_and_oracle_arithmetic():
    result = study.one_case(('iid_normal', 504, 1), replicas=10)
    oracle = result['methods'][-1]
    assert oracle['upper']-oracle['lower'] == pytest.approx(2*study.Z*.01/np.sqrt(504))
    for row in result['methods']:
        assert sum((row['covers'], row['misses_above'], row['misses_below'])) == 1


def test_incomplete_study_rejected():
    with pytest.raises(ValueError, match='Incomplete'):
        study.summarize([])

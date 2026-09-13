"""Offline comparison of the same frozen inputs in two actual Python environments.

No server, database, provider, holdout data or portfolio writes. Optional input is
a JSON list of {name, snapshot, expected_result} from synthetic saved reports.
All comparisons are exact; differences are reported rather than hidden by a
post-hoc tolerance. This diagnoses portability, not statistical coverage.
"""
import argparse
from datetime import date, timedelta
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import numpy as np
from atlas_quant.quality import digest
from atlas_quant.robustness import evaluate, stationary_means, NUMPY_VERSION

POLICY = 'atlas-robustness-cross-environment-v1'


def fixture(intervals, varying):
    dates = [(date(2020, 1, 1) + timedelta(days=i)).isoformat()
             for i in range(intervals + 3)]
    curve = []
    with localcontext() as ctx:
        ctx.prec = 64
        sma = hold = Decimal('1000')
        for i, day in enumerate(dates):
            if varying:
                sma *= 1 + Decimal((i % 17) - 8) / 10000
                hold *= 1 + Decimal((i % 13) - 6) / 10000
                sma = sma.quantize(Decimal('0.000000000001'))
                hold = hold.quantize(Decimal('0.000000000001'))
            curve.append(dict(date=day, sma_eur=str(sma), buy_hold_eur=str(hold), cash_eur='1000'))
    development = dict(sessions=len(dates), curve=curve,
        trades=[dict(strategy='Comprar y mantener', side='buy', date=dates[0])])
    development['report_hash'] = digest(development)
    return dict(protocol=dict(slow=3, holdout_date='2030-01-01', start_date=dates[0]),
        session_dates=dates, config=dict(policy='sma-economics-eur-v1', initial_cash_eur='1000'),
        source=dict(currency='EUR', price_basis='raw', basis_verified=True,
                    corporate_policy='verified-event-free-v1'), development=development)


def source_hash():
    files = [Path(__file__), *(ROOT / 'backend/atlas_quant' / name for name in
             ('robustness.py', 'robustness_contracts.py', 'quality.py'))]
    return digest({p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in files})


def run(extra):
    if np.__version__ != NUMPY_VERSION:
        raise ValueError(f'Requires NumPy {NUMPY_VERSION}')
    cases = [dict(name='constant-504', snapshot=fixture(504, False)),
             dict(name='varying-504', snapshot=fixture(504, True)),
             dict(name='varying-2000', snapshot=fixture(2000, True)),
             dict(name='insufficient-4', snapshot=fixture(4, True))]
    if extra:
        supplied = json.loads(extra.read_text(encoding='utf-8'))
        if not isinstance(supplied, list) or len(supplied) > 8:
            raise ValueError('Supply at most eight frozen synthetic cases')
        cases.extend(supplied)
    names = [case['name'] for case in cases]
    if len(set(names)) != len(names):
        raise ValueError('Case names must be unique')
    inputs_hash = digest(cases)
    pairs = np.c_[np.arange(4) / 10, np.zeros(4)]
    means, indices = stationary_means(pairs, 2, 17, replicas=4)
    oracle_ok = (indices == '897cf9280f5cb26dc8bcf186b05d4c22efed77dc4a1f81c181bae05a4df154d4'
                 and bool(np.allclose(np.quantile([0., 1., 2., 3.], [.025, .975], method='linear'),
                                      [.075, 2.925], rtol=0., atol=1e-15)))
    results = []
    for case in cases:
        result = evaluate(case['snapshot'])
        expected = case.get('expected_result')
        results.append(dict(name=case['name'], snapshot_hash=digest(case['snapshot']), result=result,
            stored_result_matches=None if expected is None else result == expected))
        print(f"{case['name']}: {result['status']}", flush=True)
    return dict(policy=POLICY, source_hash=source_hash(), inputs_hash=inputs_hash,
        environment=dict(python=platform.python_version(), system=platform.system(),
                         machine=platform.machine(), platform=platform.platform(), numpy=np.__version__),
        oracle=dict(passed=oracle_ok, indices_hash=indices, means=means.tolist()), cases=results)


def compare(left, right):
    for report in (left, right):
        if report.get('policy') != POLICY or not report.get('cases'):
            raise ValueError('Unsupported or empty comparison input')
    names = [case['name'] for case in left['cases']]
    same_cases = names == [case['name'] for case in right['cases']]
    checks = dict(same_source=left['source_hash'] == right['source_hash'],
        same_inputs=left['inputs_hash'] == right['inputs_hash'], same_cases=same_cases,
        different_system=left['environment']['system'] != right['environment']['system'],
        fixed_numpy=left['environment']['numpy'] == right['environment']['numpy'] == NUMPY_VERSION,
        oracle_passed=left['oracle']['passed'] is True and right['oracle']['passed'] is True,
        same_oracle=left['oracle'] == right['oracle'])
    comparisons = []
    if same_cases:
        for a, b in zip(left['cases'], right['cases']):
            comparisons.append(dict(name=a['name'], exact=a == b,
                stored_results_match=a['stored_result_matches'] is not False and
                                     b['stored_result_matches'] is not False))
    passed = all(checks.values()) and bool(comparisons) and all(
        row['exact'] and row['stored_results_match'] for row in comparisons)
    return dict(policy=POLICY, passed=passed, checks=checks, cases=comparisons,
                environments=[left['environment'], right['environment']])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    execute = commands.add_parser('run')
    execute.add_argument('--input', type=Path)
    execute.add_argument('--output', type=Path, required=True)
    check = commands.add_parser('compare')
    check.add_argument('left', type=Path)
    check.add_argument('right', type=Path)
    check.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'run':
        result = run(args.input)
        ok = result['oracle']['passed'] and all(c['stored_result_matches'] is not False for c in result['cases'])
    else:
        result = compare(*(json.loads(p.read_text(encoding='utf-8')) for p in (args.left, args.right)))
        ok = result['passed']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(dict(output=str(args.output), passed=ok)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

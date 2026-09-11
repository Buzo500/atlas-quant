"""Run the v0.6 SMA 20/50 reference with synthetic data, without starting ATLAS."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from atlas_quant.quality import digest
from atlas_quant.strategy_spec import CloseObservation, SmaSpec, EVALUATOR_VERSION
from atlas_quant.strategy_evaluator import dump_checkpoint, evaluate, initial_state, load_checkpoint, replay


def run_reference():
    """50 equal closes, upward cross, equality, downward cross: two intents."""
    prices = ['100'] * 50 + ['110', '90', '80']
    days = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(len(prices) + 1)]
    spec = SmaSpec.model_validate_json(json.dumps(dict(
        strategy_id='sma20-50-reference', revision=1,
        source=dict(kind='synthetic', id='sma-reference-closes', version=1,
            sha256=digest(prices), instrument_id='SYNTHETIC', listing_id='SYNTHETIC.EUR',
            market='XTEST', basis_verified=True,
            evidence_sha256=digest({'source': 'synthetic-reference', 'events': []})),
        calendar=dict(id='synthetic-daily', version=1, verified=True, market='XTEST', timezone='UTC',
            source='Synthetic daily schedule; not evidence about a real exchange',
            sessions=[dict(date=day, open_at=day+'T09:00:00Z', close_at=day+'T17:00:00Z') for day in days]),
    )))
    observations = [CloseObservation(
        spec_hash=spec.fingerprint, session_index=i, close=price,
        available_at=days[i]+'T17:01:00Z', decision_at=days[i]+'T17:02:00Z',
    ) for i, price in enumerate(prices)]
    batch = replay(spec, observations)
    state = initial_state(spec)
    recovered = []
    for observation in observations:
        result = evaluate(spec, state, observation)
        recovered.append(result)
        state = load_checkpoint(spec, dump_checkpoint(result.state))
    return dict(
        format='atlas-sma-reference-v1', evaluator=EVALUATOR_VERSION,
        synthetic=True, ordinary_data_touched=False, execution_implemented=False,
        spec=spec.model_dump(mode='json'), spec_hash=spec.fingerprint,
        observations=[item.model_dump(mode='json') for item in observations],
        decisions=[item.model_dump(mode='json') for item in batch],
        intents=[item.intent.model_dump(mode='json') for item in batch if item.intent],
        checkpoint=json.loads(dump_checkpoint(state)), replay_incremental_parity=tuple(recovered) == batch,
        code_sha256={name: hashlib.sha256((ROOT/'backend/atlas_quant'/name).read_bytes()).hexdigest()
                     for name in ('strategy_spec.py', 'strategy_evaluator.py')},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Write the synthetic report here instead of stdout.')
    args = parser.parse_args()
    result = run_reference()
    if not result['replay_incremental_parity']:
        parser.exit(1, 'La referencia no conserva paridad.\n')
    document = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document, encoding='utf-8')
        print(json.dumps(dict(report=str(args.output.resolve()), synthetic=True,
            intents=len(result['intents']), replay_incremental_parity=True,
            ordinary_data_touched=False)))
    else:
        print(document, end='')


if __name__ == '__main__':
    main()

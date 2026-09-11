"""Reproducible, isolated v0.6 EUR simulation; no running ATLAS or credentials needed."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))

from atlas_quant.quality import digest
from atlas_quant.simulation_contracts import SimulationConfig
from atlas_quant.strategy_spec import CloseObservation, OpeningObservation, SmaSpec
from atlas_quant.strategy_simulation import SmaSimulation, restore_simulation, simulate, MAX_CHECKPOINT_BYTES
from run_sma_reference import run_reference

FORMAT = 'atlas-sma-economic-reference-v1'


def code_hashes():
    paths = ['backend/atlas_quant/'+name for name in (
        'strategy_spec.py', 'strategy_evaluator.py', 'simulation_contracts.py',
        'strategy_simulation.py', 'book.py', 'quality.py')]
    paths += ['tools/run_sma_reference.py', 'tools/run_sma_simulation.py']
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths}


def reference_inputs():
    source = run_reference()
    spec_document = source['spec']
    rows = [dict(date=session['date'], open='80' if i == 53 else '100',
                 close=source['observations'][i]['close'] if i < 53 else None)
            for i, session in enumerate(spec_document['calendar']['sessions'])]
    spec_document['source']['id'] = 'sma-economic-synthetic'
    spec_document['source']['sha256'] = digest(rows)
    spec = SmaSpec.model_validate_json(json.dumps(spec_document))
    settings = SimulationConfig(initial_cash_eur='1000', quantity_step='1', fixed_fee_eur='1',
                                fee_bps='0', slippage_bps='0')
    stream = []
    for i, row in enumerate(rows):
        session = spec.calendar.sessions[i]
        stream.append(OpeningObservation(spec_hash=spec.fingerprint, open_at=session.open_at,
            decision_at=session.open_at, available_at=session.open_at, price=row['open']))
        if row['close']:
            stream.append(CloseObservation(spec_hash=spec.fingerprint, session_index=i, close=row['close'],
                available_at=row['date']+'T17:01:00Z', decision_at=row['date']+'T17:02:00Z'))
    return spec, settings, stream


def run_economic_reference():
    spec, settings, stream = reference_inputs()
    batch = simulate(spec,settings,stream)
    incremental = SmaSimulation(spec,settings)
    for event in stream:
        incremental.process(event)
        incremental = restore_simulation(spec,settings,incremental.checkpoint())
    result = batch.report()
    if incremental.report() != result:
        raise ValueError('Replay y recuperación económica difieren.')
    return dict(format=FORMAT, synthetic=True, ordinary_data_touched=False,
                result=result, result_sha256=digest(result), code_sha256=code_hashes(),
                checkpoint=json.loads(batch.checkpoint()), replay_incremental_parity=True)


def reproduce(document):
    if len(document.encode('utf-8')) > MAX_CHECKPOINT_BYTES:
        raise ValueError('Informe demasiado grande.')
    saved = json.loads(document)
    if saved.get('format') != FORMAT or digest(saved.get('result')) != saved.get('result_sha256'):
        raise ValueError('Formato o huella del informe incorrectos.')
    if saved.get('code_sha256') != code_hashes():
        raise ValueError('El código difiere del que generó el informe.')
    result = saved['result']
    spec = SmaSpec.model_validate_json(json.dumps(result['spec']))
    settings = SimulationConfig.model_validate_json(json.dumps(result['config']))
    simulation = restore_simulation(spec,settings,json.dumps(saved['checkpoint']))
    if simulation.report() != result:
        raise ValueError('El resultado no coincide con la reconstrucción de sus eventos.')
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Write the complete reference to a new file.')
    parser.add_argument('--reproduce', type=Path, help='Verify an existing reference against its events and code.')
    args = parser.parse_args()
    try:
        if args.reproduce:
            with args.reproduce.open('rb') as stream:
                document = stream.read(MAX_CHECKPOINT_BYTES+1)
            if len(document) > MAX_CHECKPOINT_BYTES:
                raise ValueError('Informe demasiado grande.')
            result = reproduce(document.decode('utf-8'))
        else:
            result = run_economic_reference()
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            # Do not overwrite existing reports, source files, or local databases.
            with args.output.open('x',encoding='utf-8') as stream:
                json.dump(result,stream,ensure_ascii=False,indent=2)
                stream.write('\n')
        fills = [e for e in result['result']['executions'] if e['status']=='filled']
        print(json.dumps(dict(report=str(args.output.resolve()) if args.output else None,
            reproduced=bool(args.reproduce), synthetic=result['synthetic'], fills=len(fills),
            final_nav_eur=result['result']['final']['nav_eur'], replay_incremental_parity=True,
            ordinary_data_touched=False)))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f'No se pudo completar la referencia: {exc}\n')


if __name__ == '__main__':
    main()

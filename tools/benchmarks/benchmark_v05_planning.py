"""Planning latency and memory on the existing 100k-price/10k-movement fixture."""
import json
import os
import time
import tracemalloc
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from benchmark_d6_valuation import ROOT,seed,confirm
from atlas_quant.targets_contracts import TargetDraftInput,TargetActivateInput,TargetSpec
from atlas_quant.targets_service import TargetsService
from atlas_quant.valuation_service import ValuationService
from atlas_quant.valuation_contracts import ValuationInput
from atlas_quant.planning_contracts import PlanningInput,PlanningReport
from atlas_quant.planning_service import PlanningService
from atlas_quant.controls import update_settings
from atlas_quant.store import Store


def main():
    directory=ROOT/'var/validation'/('v05-planning-load-'+uuid4().hex)
    directory.mkdir(parents=True)
    os.environ['ATLAS_DATA_DIR']=str(directory)
    store,p,day=seed(directory)
    catalog=store.read(lambda w:w.catalog())
    rows=[dict(instrument_id=i['id'],weight='5',minimum='0',maximum='10',concentration_limit='10') for i in catalog['instruments']]
    rows.append(dict(instrument_id=None,weight='50',minimum='40',maximum='100',concentration_limit='100'))
    targets=TargetsService(store)
    target=confirm(lambda b:targets.review(p['id'],b,'draft'),TargetDraftInput(expected_revision=p['revision'],expected_targets_revision=0,spec=TargetSpec(name='Carga sintética de planificación',rows=rows)))['target']
    confirm(lambda b:targets.review(p['id'],b,'activate'),TargetActivateInput(expected_revision=p['revision'],expected_targets_revision=1,target_id=target['id']))
    cut=confirm(lambda b:ValuationService(store).calculate(p['id'],b),ValuationInput(expected_revision=p['revision'],as_of_date=day))['cut']
    rules=[dict(listing_id=l['id'],quantity_step='1',fixed_fee='1',fee_bps='5',priority=0) for l in catalog['listings']]
    body=PlanningInput(kind='allocation',expected_revision=p['revision'],expected_targets_revision=2,cut_id=cut['id'],use_existing_cash=True,rules=rules)
    service=PlanningService(store)
    def calculate():
        start=time.perf_counter()
        report=service.calculate(p['id'],body)['report']
        PlanningReport.model_validate(report).model_dump_json()
        assert len(report['result']['variants'][0]['trades'])==10
        return time.perf_counter()-start
    timings=[calculate() for _ in range(5)]
    tracemalloc.start();calculate();_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    control_store=Store(store.path);controls=[]
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(lambda:[calculate() for _ in range(3)])
        for _ in range(20):
            start=time.perf_counter();update_settings(control_store,{'kill_switch':True});controls.append(time.perf_counter()-start)
        future.result()
    result=dict(directory=str(directory),price_bars=100000,fx_observations=10000,movements=10000,listings=10,
        calculation_and_serialization_seconds=timings,python_peak_mib=peak/1024**2,
        control_p95_seconds=sorted(controls)[18],control_boundary='application services, separate Store',ordinary_data_touched=False)
    result['passed']=max(timings)<5 and peak<256*1024**2 and result['control_p95_seconds']<1
    (directory/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

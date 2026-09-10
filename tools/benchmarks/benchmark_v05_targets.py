"""Bounded target analysis over the D6 load fixture; no worker or external data."""
import json
import os
import time
import tracemalloc
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from benchmark_d6_valuation import ROOT, seed, confirm
from atlas_quant.catalog import CatalogService
from atlas_quant.targets_contracts import TargetDraftInput, TargetActivateInput, TargetEvaluationInput, TargetSpec
from atlas_quant.targets_service import TargetsService
from atlas_quant.valuation_service import ValuationService
from atlas_quant.valuation_contracts import ValuationInput


def main():
    directory=ROOT/'var/validation'/('v05-load-'+uuid4().hex)
    directory.mkdir(parents=True,exist_ok=False)
    os.environ['ATLAS_DATA_DIR']=str(directory)
    store,p,end=seed(directory)
    cat=CatalogService(store)
    catalog=cat.read()
    while len(catalog['instruments'])<199:
        catalog=cat.add('instrument',dict(expected_revision=catalog['revision'],name='Carga sintética '+str(len(catalog['instruments'])),source='Fixture v0.5'))
    rows=[dict(instrument_id=i['id'],weight='0',minimum='0',maximum='100',concentration_limit='100') for i in catalog['instruments']]
    rows.append(dict(instrument_id=None,weight='100',minimum='0',maximum='100',concentration_limit='100'))
    service=TargetsService(store)
    draft=confirm(lambda b:service.review(p['id'],b,'draft'),TargetDraftInput(expected_revision=p['revision'],expected_targets_revision=0,
        spec=TargetSpec(name='Carga de 200 objetivos sintéticos',rows=rows)))['target']
    confirm(lambda b:service.review(p['id'],b,'activate'),TargetActivateInput(expected_revision=p['revision'],expected_targets_revision=1,target_id=draft['id']))
    cut=confirm(lambda b:ValuationService(store).calculate(p['id'],b),ValuationInput(expected_revision=p['revision'],as_of_date=end))['cut']
    body=TargetEvaluationInput(expected_revision=p['revision'],expected_targets_revision=2,cut_id=cut['id'])
    times=[]
    for _ in range(20):
        start=time.perf_counter(); result=service.evaluate(p['id'],body)['report'];times.append(time.perf_counter()-start)
        assert result['status']=='complete' and len(result['rows'])==200
    tracemalloc.start(); service.evaluate(p['id'],body); _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    from atlas_quant.app import create_app
    from fastapi.testclient import TestClient
    controls=[]
    with TestClient(create_app(directory,run_worker=False)) as client,ThreadPoolExecutor(1) as pool:
        future=pool.submit(lambda:[service.evaluate(p['id'],body) for _ in range(20)])
        for _ in range(20):
            start=time.perf_counter()
            reply=client.post('/api/settings',json={'kill_switch':True},headers={'X-Atlas-Client':'local-v1'})
            assert reply.status_code==200 and reply.json()['kill_switch'] is True
            controls.append(time.perf_counter()-start)
        future.result()
    report=dict(directory=str(directory),price_bars=100000,movements=10000,target_rows=200,seconds=times,
        maximum_seconds=max(times),python_peak_mib=peak/1024**2,control_p95_seconds=sorted(controls)[18],
        control_boundary='ASGI, excludes browser/proxy',ordinary_data_touched=False)
    report['passed']=max(times)<1 and peak<32*1024**2 and report['control_p95_seconds']<1
    (directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

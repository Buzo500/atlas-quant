"""D8 load, ASGI controls and recovery; fresh synthetic data, no network/worker."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
import gc
import json
import os
import time
import tracemalloc
from uuid import uuid4

from benchmark_d6_valuation import ROOT, seed, confirm
from atlas_quant.backup import create_backup, restore_backup
from atlas_quant.performance_service import PerformanceService
from atlas_quant.performance_contracts import PerformanceInput, PerformanceReport
from atlas_quant.valuation_service import ValuationService
from atlas_quant.valuation_contracts import ValuationInput, ValuationCut
from atlas_quant.store import Store
from atlas_quant.worker_lock import WorkerLock


def measure(call):
    call()
    timings=[]
    for _ in range(5):
        started=time.perf_counter()
        call()
        timings.append(time.perf_counter()-started)
    gc.collect()
    tracemalloc.start()
    call()
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(seconds=timings,python_peak_mib=peak/1024**2)


def main():
    directory=ROOT/'var/validation'/('d8-delivery-'+uuid4().hex)
    directory.mkdir(parents=True,exist_ok=False)
    os.environ['ATLAS_DATA_DIR']=str(directory)
    # Import only after selecting disposable data: the module's default app also
    # opens this path, never the user's ordinary database.
    from atlas_quant.app import create_app, ExperimentInput
    from atlas_quant.service import Service
    from fastapi.testclient import TestClient
    store,p,end=seed(directory)
    application=Service(store)
    demo=application.load_demo()
    jobs=[]
    for i in range(10):
        job=application.create_experiment(ExperimentInput(dataset_id=demo['id'],symbol=demo['bars'][0]['symbol'],hours=1,
            prompt='Control sintético sin ejecución de trabajo',provider='none',budget_usd=0,auto_paper=False).model_dump())
        jobs.append(job['id'])
    nav=ValuationService(store)
    reports=PerformanceService(store)
    nav_body=ValuationInput(as_of_date=end,expected_revision=p['revision'])
    start=(date.fromisoformat(end)-timedelta(days=3660)).isoformat()
    report_body=PerformanceInput(start_date=start,end_date=end,expected_revision=p['revision'])
    def nav_call():
        value=nav.calculate(p['id'],nav_body)['cut']
        assert value['status']=='complete' and value['value']=='89910.10'
        return ValuationCut.model_validate(value).model_dump_json()
    def report_call():
        value=reports.calculate(p['id'],report_body)['report']
        assert value['pnl']['display_value']=='-32.85' and value['costs_eur']['value']=='32.85'
        assert value['external_net']['value']=='0'
        # 100000 USD less .01 fees through day 6339/9989, at .9 EUR/USD;
        # TWR uses exact NAV, not the cent-rounded display values.
        expected=Decimal('89910.099')/Decimal('89942.949')-1
        assert abs(Decimal(value['twr']['value'])-expected)<Decimal('1e-25')
        assert value['mwr']['value'] is not None
        return PerformanceReport.model_validate(value).model_dump_json()
    nav_measure=measure(nav_call)
    print(json.dumps(dict(stage='NAV',**nav_measure)),flush=True)
    period_measure=measure(report_call)
    print(json.dumps(dict(stage='period',**period_measure)),flush=True)
    controls=[]
    with TestClient(create_app(directory,run_worker=False)) as client, ThreadPoolExecutor(1) as pool:
        future=pool.submit(lambda:[report_call() for _ in range(3)])
        for i in range(20):
            started=time.perf_counter()
            response=client.post('/api/settings' if i%2==0 else f'/api/experiments/{jobs[i//2]}/control',
                json={'kill_switch':True} if i%2==0 else {'action':'pause'},headers={'X-Atlas-Client':'local-v1'})
            assert response.status_code==200,response.text
            assert response.json().get('kill_switch',response.json().get('status')) in (True,'paused')
            controls.append(time.perf_counter()-started)
            time.sleep(.03)
        future.result()
        state=client.get('/api/state')
        assert state.status_code==200
        assert 'points' not in state.json() and 'performance' not in state.json()
    saved_nav=confirm(lambda b:nav.calculate(p['id'],b),nav_body)['cut']
    saved_report=confirm(lambda b:reports.calculate(p['id'],b),report_body)['report']
    snapshot=create_backup(store.path,directory/'backups')
    target=directory/'recovered.sqlite3'
    restore_backup(snapshot,target,directory/'before',instance_lock=WorkerLock(directory/'restore.lock'))
    recovered=Store(target)
    assert ValuationService(recovered).read(p['id'],saved_nav['id'])==saved_nav
    assert PerformanceService(recovered).read(p['id'],saved_report['id'])==saved_report
    result=dict(directory=str(directory),bars=100_000,fx_observations=10_000,movements=10_000,listings=10,
        extra_control_fixture='one legacy demo plus ten queued zero-budget experiments; no worker started',period_days=3660,
        nav=nav_measure,period=period_measure,controls_seconds=controls,control_p95_seconds=sorted(controls)[18],
        control_boundary='ASGI HTTP, no browser/Node proxy',recovery_exact=True,ordinary_data_touched=False)
    result['passed']=all(max(x['seconds'])<=5 and x['python_peak_mib']<=256 for x in (nav_measure,period_measure)) and result['control_p95_seconds']<1
    (directory/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())

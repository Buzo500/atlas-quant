"""Offline asset-analysis load and control latency on a fresh isolated fixture."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import json
import time
import tracemalloc
from uuid import uuid4
from benchmark_d6_valuation import ROOT, seed
from atlas_quant.asset_analysis_contracts import AssetAnalysisInput, AssetAnalysisReport
from atlas_quant.asset_analysis_service import AssetAnalysisService
from atlas_quant.controls import update_settings
from atlas_quant.store import Store


def main():
    directory=ROOT/'var/validation'/('v05-asset-analysis-load-'+uuid4().hex)
    directory.mkdir(parents=True,exist_ok=False)
    store,_,end=seed(directory)
    service=AssetAnalysisService(store)
    catalog=service.catalog()
    body=AssetAnalysisInput(sources=[s['ref'] for s in catalog['sources']],fx=catalog['fx'][0]['ref'],
        start_date=(date.fromisoformat(end)-timedelta(days=3659)).isoformat(),end_date=end)
    def calculate():
        started=time.perf_counter()
        report=service.calculate(body)['report']
        AssetAnalysisReport.model_validate(report).model_dump_json()
        assert len(report['result']['profiles'])==10
        assert all(p['status']=='complete' for p in report['result']['profiles'])
        assert report['result']['correlations']['observations']==3659
        assert all(c['reason']=='constant_return_series' for c in report['result']['correlations']['cells'])
        return time.perf_counter()-started
    timings=[calculate() for _ in range(3)]
    tracemalloc.start(); calculate(); _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    controls=[]; control_store=Store(store.path)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(lambda:[calculate() for _ in range(2)])
        for _ in range(20):
            started=time.perf_counter();update_settings(control_store,{'kill_switch':True});controls.append(time.perf_counter()-started)
        future.result()
    result=dict(directory=str(directory),price_bars=100000,fx_observations=10000,movements=10000,sources=10,
        compared_sessions=3660,calculation_and_serialization_seconds=timings,python_peak_mib=peak/1024**2,
        control_p95_seconds=sorted(controls)[18],control_boundary='application services, separate Store',ordinary_data_touched=False)
    result['passed']=max(timings)<5 and peak<256*1024**2 and result['control_p95_seconds']<1
    (directory/'report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())

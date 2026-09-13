"""Preregistered temporal group experiment; offline, resumable, no product changes."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'backend'), str(ROOT/'tools'), str(Path(__file__).parent)]
import numpy as np
from atlas_quant.quality import digest
from atlas_quant.robustness import NUMPY_VERSION, stationary_means
from atlas_runtime import InstanceLock, atomic_json
from dependence_study import DGPS, Z, mean_variance
from robustness_coverage import wilson

PROTOCOL = 'atlas-dependence-groups-v1'
SIZES, HISTORIES, REPLICAS = (504,1008,2016), 1000, 5000
SEEDS = (20260916,20260917)
T = {4:3.182446305284263, 8:2.3646242515927844}
CODE = ('tools/diagnostics/dependence_groups.py', 'tools/diagnostics/dependence_study.py',
        'tools/diagnostics/robustness_coverage.py', 'backend/atlas_quant/robustness.py',
        'backend/atlas_quant/quality.py', 'docs/v0_6_dependencia_grupos_plan.md')


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',',':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def seed_payload(seed, dgp, n, history, method):
    return dict(protocol=PROTOCOL, seed=seed, dgp=dgp, n=n, history=history, method=method)


def derived(payload):
    return int.from_bytes(hashlib.sha256(encoded(payload)).digest()[:16], 'big')


def sample(payload):
    dgp,n = payload['dgp'],payload['n']
    rng = np.random.Generator(np.random.PCG64(derived(payload)))
    if dgp == 'iid_student5':
        return rng.standard_t(5,n)*.01*math.sqrt(3/5)
    noise = rng.normal(0,.01,n)
    values = noise.copy()
    if dgp.startswith('ar1_'):
        phi = float(dgp.split('_')[1])
        for i in range(1,n):
            values[i] = phi*values[i-1]+math.sqrt(1-phi**2)*noise[i]
    elif dgp == 'mean_break':
        values[:n//2] -= .005
        values[n//2:] += .005
    elif dgp != 'iid_normal':
        raise ValueError('Unknown DGP')
    return values


def bounds(method, lower, upper, **extra):
    valid = math.isfinite(lower) and math.isfinite(upper) and lower <= upper
    return dict(method=method, status='complete' if valid else 'nonfinite',
        lower=lower if valid else None, upper=upper if valid else None,
        covers=bool(valid and lower <= 0 <= upper), misses_above=bool(valid and lower > 0),
        misses_below=bool(valid and upper < 0), **extra)


def group_interval(values, q):
    values = np.asarray(values, dtype=np.float64)
    if q not in T or values.ndim != 1 or len(values) < q or len(values)%q or not np.isfinite(values).all():
        raise ValueError('Finite equal-sized groups required')
    groups = values.reshape(q,-1).mean(axis=1)
    center = float(groups.mean())
    se = math.sqrt(float(np.sum((groups-center)**2))/(q*(q-1)))
    details = dict(group_means=groups.tolist(), center=center, se=se, t_quantile=T[q], df=q-1)
    if se == 0:
        return dict(method=f'q{q}', status='degenerate', lower=None, upper=None, covers=False,
                    misses_above=False, misses_below=False, **details)
    return bounds(f'q{q}',center-T[q]*se,center+T[q]*se,**details)


def group_covariance(n, q, phi, sigma=.01):
    if n%q or n < q or not -1 < phi < 1:
        raise ValueError('Invalid grouped AR(1)')
    m = n//q
    result = np.eye(q)*mean_variance(m,phi,sigma)
    # Sum covariance across adjacent blocks, then decay by distance in blocks.
    cross = sigma**2 * phi * ((1-phi**m)/(1-phi))**2 / m**2
    for i in range(q):
        for j in range(i+1,q):
            result[i,j] = result[j,i] = cross * phi**((j-i-1)*m)
    return result


def peak_memory():
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)] + [
                (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
                'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL('kernel32'); kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL('psapi')
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            return counters.PeakWorkingSetSize
        return None
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024


def one_case(job, replicas=REPLICAS):
    seed,dgp,n,history = job
    source_payload = seed_payload(seed,dgp,n,history,'source')
    bootstrap_payload = seed_payload(seed,dgp,n,history,'stationary_L10')
    values = sample(source_payload)
    source = dict(seed_payload=source_payload, seed_json=encoded(source_payload).decode(),
                  seed_sha256=digest(source_payload), returns=values.tolist())
    methods = [group_interval(values,q) for q in (4,8)]
    means,index_hash = stationary_means(np.c_[values,np.zeros(n)],10,derived(bootstrap_payload),replicas=replicas)
    lower,upper = np.quantile(means,[.025,.975],method='linear')
    methods.append(bounds('L10',float(lower),float(upper),replicas=replicas,
        indices_hash=index_hash,seed_payload=bootstrap_payload,
        bootstrap_mean_bias=float(means.mean()-values.mean())))
    if dgp == 'iid_normal' or dgp.startswith('ar1_'):
        phi = 0. if dgp == 'iid_normal' else float(dgp.split('_')[1])
        half = Z*math.sqrt(mean_variance(n,phi))
        methods.append(bounds('oracle',float(values.mean())-half,float(values.mean())+half,true_phi=phi))
    result = dict(seed=seed,dgp=dgp,n=n,history=history,source=source,source_hash=digest(source),
                  sample_mean=float(values.mean()),methods=methods)
    return dict(**result,case_hash=digest(result))


def worker(job):
    return one_case(job), peak_memory()


def summarize(cases, histories=HISTORIES, sizes=SIZES, dgps=DGPS):
    rows, paired, correlations = [], [], []
    for dgp,n in itertools.product(dgps,sizes):
        cell = sorted([r for r in cases if r['dgp']==dgp and r['n']==n],key=lambda r:r['history'])
        if len(cell)!=histories or [r['history'] for r in cell] != list(range(histories)):
            raise ValueError('Incomplete or duplicate histories')
        by_method = {m['method']:[next(x for x in r['methods'] if x['method']==m['method']) for r in cell]
                     for m in cell[0]['methods']}
        for method,results in by_method.items():
            valid = [r for r in results if r['status']=='complete']
            widths = [r['upper']-r['lower'] for r in valid]
            hits = sum(r['covers'] for r in results)
            ratios = [(r['upper']-r['lower'])/(o['upper']-o['lower'])
                for r,o in zip(results,by_method.get('oracle',[])) if r['status']=='complete']
            rows.append(dict(dgp=dgp,n=n,method=method,histories=histories,stationary=dgp!='mean_break',
                covered=hits,coverage=hits/histories,wilson_95=wilson(hits,histories),
                invalid=histories-len(valid),sample_mean_bias=float(np.mean([r['sample_mean'] for r in cell])),
                width_quantiles=np.quantile(widths,[0,.25,.5,.75,.95,1]).tolist() if widths else None,
                width_oracle_quantiles=np.quantile(ratios,[.5,.95]).tolist() if ratios else None,
                misses_above=sum(r['misses_above'] for r in results),misses_below=sum(r['misses_below'] for r in results)))
        for b in ('q8','L10'):
            counter = Counter(f"{int(a['covers'])}{int(other['covers'])}" for a,other in zip(by_method['q4'],by_method[b]))
            paired.append(dict(dgp=dgp,n=n,a='q4',b=b,counts={k:counter[k] for k in ('00','01','10','11')}))
        for method in ('q4','q8'):
            matrix = np.asarray([r['group_means'] for r in by_method[method]])
            correlations.append(dict(dgp=dgp,n=n,method=method,adjacent_across_histories=[
                float(np.corrcoef(matrix[:,i],matrix[:,i+1])[0,1]) for i in range(matrix.shape[1]-1)]))
    failed = []
    for r in rows:
        if r['method']!='q4' or not r['stationary']:
            continue
        reasons = []
        if r['invalid']: reasons.append('invalid')
        if not .93 <= r['coverage'] <= .99: reasons.append('coverage')
        if r['wilson_95'][0] < .92: reasons.append('wilson_lower')
        ratios = r['width_oracle_quantiles']
        if ratios is not None and (ratios[0] > 3 or ratios[1] > 10): reasons.append('width')
        if reasons: failed.append(dict(dgp=r['dgp'],n=r['n'],reasons=reasons))
    return dict(summary=rows,paired=paired,group_correlations=correlations,
                candidate_passed=not failed,failed_cells=failed,product_promotion=False)


def key(job):
    return f'{job[1]}-{job[2]}-{job[3]:04}.json'


def fingerprints():
    return {name:hashlib.sha256((ROOT/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in CODE}


def load_case(path, job):
    value = json.loads(path.read_text(encoding='utf-8'))
    if tuple(value[k] for k in ('seed','dgp','n','history')) != job:
        raise ValueError('Case identity mismatch')
    if value['case_hash'] != digest({k:v for k,v in value.items() if k!='case_hash'}) or value['source_hash'] != digest(value['source']):
        raise ValueError('Case hash mismatch')
    payload = seed_payload(*job,'source')
    if value['source']['seed_payload'] != payload or value['source']['seed_json'] != encoded(payload).decode() or value['source']['seed_sha256'] != digest(payload):
        raise ValueError('Seed manifest mismatch')
    return value


def run(output, seed, workers, confirm_from=None):
    if np.__version__ != NUMPY_VERSION or workers not in range(1,7) or seed not in SEEDS:
        raise ValueError('Fixed NumPy, seed and maximum six workers required')
    code = fingerprints()
    if seed == SEEDS[1]:
        if confirm_from is None: raise ValueError('Confirmation requires successful main evidence')
        prior = json.loads((confirm_from/'results.json').read_text(encoding='utf-8'))
        if not prior['candidate_passed'] or prior['seed'] != SEEDS[0] or prior['code_sha256'] != code or prior['result_hash'] != digest({k:v for k,v in prior.items() if k!='result_hash'}):
            raise ValueError('Main experiment did not pass unchanged')
    output.mkdir(parents=True,exist_ok=True)
    with InstanceLock(output/'study.lock'):
        jobs = list(itertools.product([seed],DGPS,SIZES,range(HISTORIES)))
        plan = dict(protocol=PROTOCOL,seed=seed,sizes=SIZES,dgps=DGPS,histories=HISTORIES,replicas=REPLICAS,
            candidate='q4',sensitivity='q8',bootstrap='stationary_L10',t_quantiles=T,
            numpy=np.__version__,python=platform.python_version(),code_sha256=code,
            thresholds=dict(coverage=[.93,.99],wilson_lower=.92,width_median=3,width_p95=10),
            max_seconds=3600,max_workers=6)
        # JSON round trip normalizes tuple and integer-key representations for resume.
        plan = json.loads(encoded(plan))
        if (output/'plan.json').exists():
            stored_plan=json.loads((output/'plan.json').read_text())
            if stored_plan['plan'] != plan or stored_plan['plan_hash'] != digest(plan): raise ValueError('Resume plan differs')
        else:
            atomic_json(output/'plan.json',dict(plan=plan,plan_hash=digest(plan),
                frozen_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
            with (output/'seeds.jsonl').open('xb') as stream:
                for job in jobs:
                    for method in ('source','stationary_L10'):
                        payload=seed_payload(*job,method)
                        stream.write(encoded(dict(payload=payload,json=encoded(payload).decode(),sha256=digest(payload)))+b'\n')
        seed_hash=hashlib.sha256()
        with (output/'seeds.jsonl').open('rb') as stream:
            for job in jobs:
                for method in ('source','stationary_L10'):
                    payload=seed_payload(*job,method)
                    expected=encoded(dict(payload=payload,json=encoded(payload).decode(),sha256=digest(payload)))+b'\n'
                    actual=stream.readline()
                    if actual!=expected: raise ValueError('Seed inventory differs')
                    seed_hash.update(actual)
            if stream.read(1): raise ValueError('Extra seed identities')
        (output/'cases').mkdir(exist_ok=True)
        missing = []
        for job in jobs:
            path=output/'cases'/key(job)
            if path.exists(): load_case(path,job)
            else: missing.append(job)
        started=time.monotonic(); completed=len(jobs)-len(missing); max_worker_memory=0
        executor=ProcessPoolExecutor(max_workers=workers)
        pending={}; queue=iter(missing); interrupted=False
        try:
            for _ in range(workers):
                job=next(queue,None)
                if job: pending[executor.submit(worker,job)]=job
            while pending:
                if time.monotonic()-started >= 3600 or (output/'stop-request').exists():
                    interrupted=True; break
                done,_=wait(pending,timeout=1,return_when=FIRST_COMPLETED)
                for future in done:
                    job=pending.pop(future); value,memory=future.result()
                    max_worker_memory=max(max_worker_memory,memory or 0)
                    atomic_json(output/'cases'/key(job),value)
                    completed+=1
                    if completed%100==0:
                        progress=dict(completed=completed,total=len(jobs),seconds=round(time.monotonic()-started,1),peak_worker_bytes=max_worker_memory)
                        atomic_json(output/'progress.json',progress); print(json.dumps(progress),flush=True)
                    next_job=next(queue,None)
                    if next_job: pending[executor.submit(worker,next_job)]=next_job
        except BaseException:
            executor.terminate_workers()
            raise
        finally:
            if interrupted: executor.terminate_workers()
            else: executor.shutdown(wait=True,cancel_futures=True)
            atomic_json(output/'execution.json',dict(complete=not interrupted and completed==len(jobs),completed=completed,
                workers=workers,seconds=time.monotonic()-started,peak_worker_bytes=max_worker_memory,peak_parent_bytes=peak_memory()))
        if interrupted:
            print('Incomplete bounded batch; resume same output/seed after removing stop-request.'); return False
        rows=[]; audit=[]; inventory=hashlib.sha256()
        for job in jobs:
            value=load_case(output/'cases'/key(job),job)
            inventory.update(encoded([key(job),value['case_hash']])+b'\n')
            if job[-1] in (0,HISTORIES-1):
                repeated=one_case(job)
                if repeated != value: raise ValueError('Independent rerun mismatch')
                audit.append(dict(case=key(job),case_hash=value['case_hash'],matched=True))
            value.pop('source'); rows.append(value)
        result=dict(protocol=PROTOCOL,seed=seed,code_sha256=code,plan_hash=digest(plan),
                    inventory_sha256=inventory.hexdigest(),seeds_sha256=seed_hash.hexdigest(),reproduction=audit,**summarize(rows))
        atomic_json(output/'results.json',dict(**result,result_hash=digest(result)))
        print(json.dumps(dict(complete=True,seed=seed,candidate_passed=result['candidate_passed'],failed_cells=result['failed_cells'])),flush=True)
        return True


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=SEEDS[0],choices=SEEDS)
    parser.add_argument('--workers',type=int,default=6,choices=range(1,7))
    parser.add_argument('--confirm-from',type=Path)
    args=parser.parse_args()
    if not run(args.output,args.seed,args.workers,args.confirm_from): sys.exit(2)


if __name__=='__main__': main()

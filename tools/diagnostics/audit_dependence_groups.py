"""Post-run arithmetic audit from saved vectors; stdlib only, no study imports."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--directory',type=Path,required=True)
folder=parser.parse_args().directory
started=time.monotonic()
result=json.loads((folder/'results.json').read_text())
encode=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
digest=lambda x:hashlib.sha256(encode(x)).hexdigest()
assert result['result_hash']==digest({k:v for k,v in result.items() if k!='result_hash'})
def close(a,b):
    assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-14),(a,b)
def quantile(xs,p):
    s=sorted(xs); pos=(len(s)-1)*p; i=int(pos)
    return s[i] if i==len(s)-1 else s[i]+(s[i+1]-s[i])*(pos-i)
cells=defaultdict(list)
files=sorted((folder/'cases').glob('*.json'))
assert len(files)==18000
for path in files:
    c=json.loads(path.read_text())
    assert c['case_hash']==digest({k:v for k,v in c.items() if k!='case_hash'})
    assert c['source_hash']==digest(c['source'])
    xs=c['source']['returns']; n=c['n']
    assert len(xs)==n and all(math.isfinite(x) for x in xs)
    close(statistics.fmean(xs),c['sample_mean'])
    methods={m['method']:m for m in c['methods']}
    for q,t in [(4,3.182446305284263),(8,2.3646242515927844)]:
        m=methods[f'q{q}']; block=n//q
        means=[statistics.fmean(xs[i*block:(i+1)*block]) for i in range(q)]
        for a,b in zip(means,m['group_means']): close(a,b)
        se=statistics.stdev(means)/math.sqrt(q)
        close(m['lower'],statistics.fmean(means)-t*se)
        close(m['upper'],statistics.fmean(means)+t*se)
    for m in methods.values():
        assert m['status']=='complete'
        assert m['covers']==(m['lower']<=0<=m['upper'])
        cells[c['dgp'],n,m['method']].append((m,methods.get('oracle')))
failures=[]
for row in result['summary']:
    cell=cells[row['dgp'],row['n'],row['method']]
    assert len(cell)==1000
    hits=sum(m['lower']<=0<=m['upper'] for m,_ in cell)
    assert hits==row['covered']
    assert row['misses_above']==sum(m['lower']>0 for m,_ in cell)
    assert row['misses_below']==sum(m['upper']<0 for m,_ in cell)
    p=hits/1000; z=statistics.NormalDist().inv_cdf(.975); den=1+z*z/1000
    center=(p+z*z/2000)/den
    margin=z*math.sqrt(p*(1-p)/1000+z*z/(4*1000**2))/den
    for a,b in zip([center-margin,center+margin],row['wilson_95']): close(a,b)
    ratios=[(m['upper']-m['lower'])/(o['upper']-o['lower']) for m,o in cell if o]
    if ratios:
        for a,b in zip([quantile(ratios,.5),quantile(ratios,.95)],row['width_oracle_quantiles']): close(a,b)
    if row['method']=='q4' and row['stationary']:
        reasons=[]
        if not .93<=p<=.99: reasons.append('coverage')
        if center-margin<.92: reasons.append('wilson_lower')
        if ratios and (quantile(ratios,.5)>3 or quantile(ratios,.95)>10): reasons.append('width')
        if reasons: failures.append(dict(dgp=row['dgp'],n=row['n'],reasons=reasons))
assert failures==result['failed_cells']
assert result['candidate_passed']==(len(failures)==0)
assert len(result['reproduction'])==36 and all(r['matched'] for r in result['reproduction'])
receipt=dict(format='atlas-groups-independent-arithmetic-audit-v1',cases=18000,
    group_intervals_checked=36000,summary_rows=len(cells),all_checks_passed=True,
    result_hash=result['result_hash'],failed_cells=failures,candidate_passed=not failures,
    seconds=time.monotonic()-started,script_sha256=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
    scope='stdlib arithmetic from saved vectors, interval coverage/Wilson/widths and gates; no bootstrap regeneration')
(folder/'independent-audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))

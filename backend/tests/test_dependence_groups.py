import importlib.util
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import pytest

spec=importlib.util.spec_from_file_location('dependence_groups',Path(__file__).resolve().parents[2]/'tools/diagnostics/dependence_groups.py')
groups=importlib.util.module_from_spec(spec)
spec.loader.exec_module(groups)


@pytest.mark.parametrize('q',[4,8])
def test_t_quantile_matches_independent_density_quadrature(q):
    # Composite Simpson integrates the Student density, independent of quantile constants.
    df=q-1; x=groups.T[q]; subdivisions=20000
    step=x/subdivisions
    coefficient=math.gamma((df+1)/2)/(math.sqrt(df*math.pi)*math.gamma(df/2))
    def density(t): return coefficient*(1+t*t/df)**(-(df+1)/2)
    area=step/3*(density(0)+density(x)+sum((4 if i%2 else 2)*density(i*step) for i in range(1,subdivisions)))
    assert abs(.5+area-.975)<1e-10


def test_group_algebra_translation_scale_and_degenerate():
    source=np.array([-3.,-1,1,3])
    result=groups.group_interval(source,4)
    assert result['center']==0 and result['se']==pytest.approx(math.sqrt(5/3),abs=1e-15)
    shift=groups.group_interval(source+7,4)
    reverse=groups.group_interval(source*-2,4)
    assert shift['lower']==pytest.approx(result['lower']+7)
    assert reverse['lower']==pytest.approx(-2*result['upper'])
    assert reverse['upper']==pytest.approx(-2*result['lower'])
    zero=groups.group_interval(np.ones(8),4)
    assert zero['status']=='degenerate' and zero['lower'] is None and not zero['covers']
    for values in ([1,2,3],[1,2,3,float('nan')]):
        with pytest.raises(ValueError): groups.group_interval(values,4)


@pytest.mark.parametrize('phi',[0.,.6,.9,.95,-.4])
def test_ar1_oracle_and_group_covariance_against_explicit_covariance_matrix(phi):
    n,q=12,4
    cov=np.array([[.0001*phi**abs(i-j) for j in range(n)] for i in range(n)])
    assert groups.mean_variance(n,phi)==pytest.approx(cov.sum()/n**2,abs=1e-17)
    exact=np.array([[cov[i*3:(i+1)*3,j*3:(j+1)*3].sum()/9 for j in range(q)] for i in range(q)])
    np.testing.assert_allclose(groups.group_covariance(n,q,phi),exact,rtol=0,atol=1e-17)


def test_seed_is_canonical_and_independent_of_order_or_method():
    payload=groups.seed_payload(123,'iid_normal',504,7,'source')
    canonical=b'{"dgp":"iid_normal","history":7,"method":"source","n":504,"protocol":"atlas-dependence-groups-v1","seed":123}'
    assert groups.encoded(payload)==canonical
    assert groups.derived(payload)==int.from_bytes(hashlib.sha256(canonical).digest()[:16],'big')
    assert groups.derived(dict(payload,method='stationary_L10'))!=groups.derived(payload)
    assert groups.derived(dict(reversed(list(payload.items()))))==groups.derived(payload)


def test_small_case_repeats_and_detects_corruption(tmp_path):
    job=(123,'ar1_0.95',16,2)
    value=groups.one_case(job,replicas=8)
    assert value==groups.one_case(job,replicas=8)
    path=tmp_path/'case.json'
    path.write_text(json.dumps(value),encoding='utf-8')
    assert groups.load_case(path,job)==value
    value['source']['returns'][0]+=1
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ValueError,match='hash'): groups.load_case(path,job)


def test_gate_does_not_rescue_q4_with_q8_or_stress():
    cases=[]
    for i in range(100):
        methods=[]
        for method in ('q4','q8','L10','oracle'):
            r=groups.bounds(method, -.5 if method!='q4' or i<90 else .1,.5)
            if method in ('q4','q8'): r['group_means']=[i,i*2+1,i*3+2,i*4+3]
            methods.append(r)
        cases.append(dict(dgp='iid_normal',n=504,history=i,sample_mean=0,methods=methods))
    summary=groups.summarize(cases,histories=100,sizes=(504,),dgps=('iid_normal',))
    assert not summary['candidate_passed'] and not summary['product_promotion']
    assert summary['failed_cells'][0]['reasons']==['coverage','wilson_lower']
    assert summary['paired'][0]['counts']=={'00':0,'01':10,'10':0,'11':90}
    with pytest.raises(ValueError): groups.summarize(cases[:-1],histories=100,sizes=(504,),dgps=('iid_normal',))

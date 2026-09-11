"""Independent arithmetic, predeclared axes, temporal isolation and publication."""
from copy import deepcopy
from decimal import localcontext, ROUND_UP
import pytest
from fastapi.testclient import TestClient
from atlas_quant.app import create_app
from atlas_quant.lab_contracts import LabReport, LabInput, POLICY
from atlas_quant.lab_sources import freeze_source
from atlas_quant.quality import digest
from atlas_quant.sensitivity import plan, evaluate
from atlas_quant.sensitivity_contracts import SensitivityConfig
from atlas_quant.walk_forward_contracts import WalkForwardConfig
from atlas_quant.store import UnitOfWork
from test_lab_v06 import lab, LOCAL, open_request  # noqa: F401
from test_walk_forward_v06 import wf  # noqa: F401


def test_cost_stress_independent_arithmetic_and_reproduction(lab):
    _, service, body = lab
    body = body.model_copy(update=dict(sensitivity=SensitivityConfig()))
    result = service.create(body)
    LabReport.model_validate(result)
    report = result['sensitivity']
    assert [c['label'] for c in report['cases']] == ['base', 'cost:2']
    assert report['cases'][0]['result'] == result['development']
    # 1000 - 99*10 - 2 + 99*8 - 2 = 798; no implicit reinvestment/fees on warm-up.
    assert [c['result']['metrics'][0]['final_nav_eur'] for c in report['cases']] == ['800', '798']
    assert report['summary']['return_spread_pp'] == '0.2'
    assert report['summary']['min_return_pct'] == '-20.2'
    assert result['holdout'] is None
    ident = result['protocol']['id']
    assert service.create(body) == result
    assert service.reproduce(ident)['sensitivity_matches'] is True
    opened = service.open_holdout(ident, open_request(ident))
    assert opened['sensitivity'] == report
    assert service.reproduce(ident)['holdout_matches'] is True


def test_walk_forward_ids_stay_identical_without_sensitivity(wf):
    _, service, body, frozen = wf
    expected = digest(dict(policy=POLICY, inputs=body.model_dump(mode='json', exclude={'sensitivity'}), frozen=frozen))
    assert service.create(body)['protocol']['id'] == expected


def test_axes_are_oat_not_cartesian_and_costs_round_up(wf):
    _, _, body, frozen = wf
    body = body.model_copy(update=dict(fast=3, slow=6, walk_forward=None, sensitivity=SensitivityConfig(
        fast_windows=[2, 4], slow_windows=[5, 7], cost_multipliers=['1', '1.001'])))
    cases = plan(body, frozen['calendar']['sessions'])
    assert [(v.fast, v.slow) for _, v in cases] == [(3,6), (2,6), (4,6), (3,5), (3,7), (3,6)]
    assert cases[-1][1].config.fixed_fee_eur == '1.01'
    assert cases[-1][1].config.initial_cash_eur == body.config.initial_cash_eur


@pytest.mark.parametrize('change', [dict(fast_windows=[2,2]), dict(slow_windows=[2]), dict(fast_windows=[True]),
    dict(cost_multipliers=['1','1.00']), dict(cost_multipliers=['11']), dict(cost_multipliers=['-1']),
    dict(cost_multipliers=['NaN']), dict(cost_multipliers=[2]), dict(extra=1)])
def test_strict_config(change):
    with pytest.raises(ValueError):
        SensitivityConfig(**change)


@pytest.mark.parametrize('config', [dict(cost_multipliers=['1']), dict(fast_windows=[3]), dict(slow_windows=[250])])
def test_invalid_or_excessive_cases_fail_before_publication(lab, config):
    _, service, body = lab
    with pytest.raises(ValueError):
        service.create(body.model_copy(update=dict(sensitivity=SensitivityConfig(**config))))
    assert service.history()['items'] == []


def test_too_many_valid_cases_are_rejected(wf):
    _, _, body, frozen = wf
    body = body.model_copy(update=dict(fast=3, slow=6, walk_forward=None,
        sensitivity=SensitivityConfig(fast_windows=[2,4,5],slow_windows=[4,5,7,8],cost_multipliers=['0','1','2'])))
    with pytest.raises(ValueError, match='ocho casos'):
        plan(body, frozen['calendar']['sessions'])


def test_combined_work_bound(wf):
    _, _, body, _ = wf
    sessions = [dict(date=f'{i:04}') for i in range(1900)]
    body = body.model_copy(update=dict(holdout_date='9999', fast=20, slow=50,
        walk_forward=WalkForwardConfig(context_sessions=900, evaluation_sessions=50),
        sensitivity=SensitivityConfig(fast_windows=[15,25],slow_windows=[40,60],cost_multipliers=['1','2','3'])))
    with pytest.raises(ValueError, match='30.000'):
        plan(body, sessions)


def test_final_prices_not_read_and_missing_data_remains_visible(wf):
    _, service, body, frozen = wf
    body = body.model_copy(update=dict(sensitivity=SensitivityConfig()))
    development = service.create(body)['development']
    expected = evaluate(frozen, body, development)
    class Protected(dict):
        def __getitem__(self, key):
            assert key < body.holdout_date
            return super().__getitem__(key)
        def get(self, key, default=None):
            assert key < body.holdout_date
            return super().get(key, default)
        def items(self):
            raise AssertionError('No final-test enumeration')
    frozen['bars'] = Protected(frozen['bars'])
    frozen['openings'] = Protected(frozen['openings'])
    with localcontext() as context:
        context.prec, context.rounding = 6, ROUND_UP
        assert evaluate(frozen, body, development) == expected
    frozen['openings'][body.start_date] = None
    result = evaluate(frozen, body, development)
    assert result['summary']['evaluable_cases'] == 0
    assert result['summary']['return_spread_pp'] is None
    assert all(not c['evaluable'] for c in result['cases'])


def test_sensitivity_http_and_atomic_failure(lab, monkeypatch):
    store, service, body = lab
    body = body.model_copy(update=dict(sensitivity=SensitivityConfig()))
    original = UnitOfWork.audit
    def fail(work, event, *args, **kwargs):
        if event == 'lab.development_saved': raise RuntimeError('audit unavailable')
        return original(work, event, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(UnitOfWork, 'audit', fail)
        with pytest.raises(RuntimeError): service.create(body)
    assert service.history()['items'] == []
    with TestClient(create_app(store.path.parent, run_worker=False)) as client:
        result = client.post('/api/lab/protocols', json=body.model_dump(mode='json'), headers=LOCAL)
        assert result.status_code == 200, result.text
        assert len(result.json()['sensitivity']['cases']) == 2
        invalid = body.model_dump(mode='json')
        invalid['sensitivity']['cost_multipliers'] = ['NaN']
        assert client.post('/api/lab/protocols', json=invalid, headers=LOCAL).status_code == 422

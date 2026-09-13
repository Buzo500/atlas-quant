import copy
import io
import json
import zipfile
import pytest
from fastapi.testclient import TestClient
from atlas_quant.app import create_app
from atlas_quant.period_report import adapt
from atlas_quant.period_latex import make_files, archive, verify_archive
from atlas_quant.performance_service import PerformanceService
from test_multicurrency_d6 import setup, body, confirm, row, dump, LOCAL
from test_performance_d7 import request

STAMP = '2026-09-13T20:00:00+00:00'


def saved(setup):
    store,books,p,_ = setup
    confirm(books,p['id'],body(setup,[row('deposit',gross_amount='1000.00'),
        row('deposit',external_id='second',date='2026-01-06',gross_amount='100.00',fee_amount='2.00')]))
    service = PerformanceService(store)
    args = request(store,p)
    preview = service.calculate(p['id'],args)
    report = service.calculate(p['id'],args.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))['report']
    return store,books,p,service,report


def test_adapter_matches_independent_deposit_cost_oracle_and_source(setup):
    store,_,_,_,report = saved(setup)
    original = copy.deepcopy(report)
    before = dump(store.path)
    model = adapt(report)
    assert model.initial_nav == '1000.00' and model.final_nav == '1098.00'
    assert model.pnl.value == '-2' and model.twr.value == '-0.002'
    assert model.external_net.value == '100' and model.costs_eur.value == '2'
    assert model.initial_state is None and model.final_state is None and model.movements is None
    assert model.detail_reason == 'not_preserved_in_source_report'
    assert report == original and dump(store.path) == before


def test_source_and_exact_csv_remain_unchanged_even_when_export_is_historical(setup):
    store,books,p,service,report = saved(setup)
    first = make_files(report, current=True, generated_at=STAMP)
    confirm(books,p['id'],body(setup,[row('deposit',external_id='later',date='2026-01-07',gross_amount='500.00')]))
    before = dump(store.path)
    zipped = service.export_latex(p['id'],report['id'])
    manifest = verify_archive(zipped)
    with zipfile.ZipFile(io.BytesIO(zipped)) as z:
        assert json.loads(z.read('source-report.json')) == report
        model = json.loads(z.read('period-report.json'))
        assert model['final_nav'] == '1098.00' and model['economic_hash'] == adapt(report).economic_hash
        assert z.read('curve.csv') == first['curve.csv'] and b'500.00' not in z.read('flows.csv')
    assert not manifest['current_at_export'] and dump(store.path) == before


def test_archive_deterministic_and_rejects_tampering_duplicates_and_paths(setup):
    *_,report = saved(setup)
    files = make_files(report, current=True, generated_at=STAMP)
    data = archive(files)
    assert data == archive(make_files(report, current=True, generated_at=STAMP))
    verify_archive(data)
    for name in ('curve.csv','source-report.json','report.tex','manifest.json'):
        changed = dict(files, **{name:files[name]+b' '})
        with pytest.raises(ValueError): verify_archive(archive(changed))
    with pytest.raises(ValueError): verify_archive(archive({**files,'../evil.tex':b'evil'}))
    buffer = io.BytesIO(data)
    with zipfile.ZipFile(buffer, 'a') as z:
        z.writestr('report.tex',b'bad')
    with pytest.raises(ValueError): verify_archive(buffer.getvalue())


def test_missing_values_and_tex_text_never_become_zero_or_commands(setup):
    *_,report = saved(setup)
    report['points'][1]['nav'] = None
    report['points'][1]['nav_exact'] = None
    report['pnl'].update(value=None,display_value=None,status='incomplete',reasons=[r'\input{private} %'])
    files = make_files(report,current=True,generated_at=STAMP)
    assert b'nan' in files['nav-plot.csv'] and b'No disponible' in files['report.tex']
    assert b'\\input{private}' not in files['report.tex'] and b'textbackslash' in files['report.tex']
    assert json.loads(files['period-report.json'])['pnl']['value'] is None


def test_unsaved_source_is_rejected_and_http_does_not_accept_client_report(setup):
    store,_,p,service,report = saved(setup)
    with pytest.raises(ValueError): adapt(dict(report,saved=False))
    before = dump(store.path)
    with TestClient(create_app(store.path.parent,run_worker=False)) as client:
        path=f'/api/v2/portfolios/{p["id"]}/performance/{report["id"]}/latex'
        assert client.post(path).status_code == 403
        result=client.post(path,headers=LOCAL,json={'report':dict(report,final_nav='999999')})
        assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
        verify_archive(result.content)
        with zipfile.ZipFile(io.BytesIO(result.content)) as z:
            assert json.loads(z.read('source-report.json'))['final_nav'] == '1098.00'
        assert client.post(path.replace(p['id'],'other'),headers=LOCAL).status_code == 404
    assert dump(store.path) == before


@pytest.mark.parametrize('value',[r'\input{private}','nan','Infinity','1e999'])
def test_plot_numeric_fields_reject_commands_and_nonfinite_values(setup,value):
    *_,report=saved(setup)
    report['points'][0]['nav']=value
    with pytest.raises(ValueError): make_files(report,current=True,generated_at=STAMP)

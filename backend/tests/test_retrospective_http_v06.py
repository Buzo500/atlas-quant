"""HTTP freezes before computation, never persists research or holdout data."""
import hashlib
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from atlas_quant.app import create_app
from atlas_quant.computation import _SLOTS
from atlas_quant.quality import digest
from atlas_quant.retrospective_package import encoded, verify_report
from test_retrospective_v06 import inputs

BASE = '/api/lab/retrospective/'
LOCAL = {'X-Atlas-Client': 'local-v1'}


@pytest.fixture
def http(tmp_path):
    app = create_app(tmp_path, run_worker=False)
    body, csv, _ = inputs()
    body.pop('source_sha256')
    with TestClient(app, headers=LOCAL) as client:
        yield client, dict(settings=body, csv=csv), tmp_path/'atlas.sqlite3'


def calculated(client, body):
    prepared = client.post(BASE+'prepare', json=body)
    assert prepared.status_code == 200, prepared.text
    p = prepared.json()
    assert 'development' not in p
    result = client.post(BASE+'calculate', json=dict(frozen_json=p['frozen_json'],
        expected_frozen_hash=p['context']['frozen_hash']))
    assert result.status_code == 200, result.text
    return p, result.json()


def test_prepare_calculate_reopen_export_preserve_database_and_reserve(http):
    client, body, database = http
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    prepared, result = calculated(client, body)
    assert result['context']['evidence_verified'] is False
    assert result['context']['holdout_evaluated'] is False
    assert [m['final_nav_eur'] for m in result['development']['metrics']] == ['800', '801', '1000']
    frozen = json.loads(prepared['frozen_json'])
    assert [r['date'] for r in frozen['rows']] == body['settings']['expected_dates'][:7]
    payload = {'report_json': result['report_json']}
    assert client.post(BASE+'reopen', json=payload).json() == result
    exported = client.post(BASE+'export', json=payload)
    assert exported.status_code == 200
    assert exported.headers['content-type'] == 'application/zip'
    assert exported.headers['cache-control'] == 'no-store'
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert len(archive.namelist()) == 7
        assert b'2025-01-08' not in archive.read('prices.csv')
        assert 'Investigación retrospectiva' in archive.read('README.txt').decode('utf-8')
        assert json.loads(archive.read('report.json')) == json.loads(result['report_json'])
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_different_code_reproduces_values_without_rewriting_original_provenance(http):
    client, body, _ = http
    _, result = calculated(client, body)
    report = json.loads(result['report_json'])
    report['code_sha256'] = {'historical-revision.py': 'a'*64}
    report['report_hash'] = digest({k:v for k,v in report.items() if k != 'report_hash'})
    with pytest.raises(ValueError, match='Código distinto'):
        verify_report(report)
    opened = client.post(BASE+'reopen', json={'report_json': encoded(report).decode()})
    assert opened.status_code == 200
    assert opened.json()['code_matches'] is False
    assert json.loads(opened.json()['report_json']) == report
    assert opened.json()['development'] == result['development']


@pytest.mark.parametrize('problem', ['assumptions', 'date_gap', 'event', 'currency', 'source_hash'])
def test_bad_preparation_never_returns_a_frozen_protocol(http, problem):
    client, body, _ = http
    if problem == 'assumptions': body['settings']['acknowledge_assumptions'] = False
    elif problem == 'date_gap': body['settings']['expected_dates'].pop(2)
    elif problem == 'event': body['csv'] = body['csv'].replace(',100,0,0', ',100,1,0', 1)
    elif problem == 'currency': body['settings']['currency'] = 'USD'
    else: body['settings']['source_sha256'] = 'f'*64
    assert client.post(BASE+'prepare', json=body).status_code == 422


@pytest.mark.parametrize('action', ['prepare', 'calculate', 'reopen', 'export'])
def test_http_origin_and_client_controls_apply(http, action):
    client, _, _ = http
    assert client.post(BASE+action, json={}, headers={'Origin':'https://untrusted.example'}).status_code == 403
    assert client.post(BASE+action, json={}, headers={'X-Atlas-Client':''}).status_code == 403


@pytest.mark.parametrize('problem', ['result', 'hash', 'reserve', 'unexpected', 'array', 'code'])
def test_reopen_and_export_reject_tampering_even_with_rehashed_report(http, problem):
    client, body, _ = http
    _, result = calculated(client, body)
    report = json.loads(result['report_json'])
    if problem == 'result': report['result']['development']['metrics'][0]['final_nav_eur'] = '999999'
    elif problem == 'hash': report['frozen']['frozen_hash'] = 'b'*64
    elif problem == 'reserve':
        report['frozen']['holdout']['prices'] = [1234]
        report['frozen']['frozen_hash'] = digest({k:v for k,v in report['frozen'].items() if k != 'frozen_hash'})
    elif problem == 'unexpected': report['secret'] = 'unexpected'
    elif problem == 'code': report['code_sha256'] = {'historical.py':'not-a-hash'}
    report['report_hash'] = digest({k:v for k,v in report.items() if k != 'report_hash'})
    document = json.dumps([report] if problem == 'array' else report)
    for action in ('reopen','export'):
        assert client.post(BASE+action, json={'report_json':document}).status_code == 422


def test_calculation_checks_selected_fingerprint(http):
    client, body, _ = http
    prepared = client.post(BASE+'prepare',json=body).json()
    response = client.post(BASE+'calculate',json={'frozen_json':prepared['frozen_json'], 'expected_frozen_hash':'f'*64})
    assert response.status_code == 422


def test_shared_computation_limit_and_recovery_leave_health_available(http):
    client, body, _ = http
    acquired = 0
    try:
        for _ in range(2):
            assert _SLOTS.acquire(blocking=False)
            acquired += 1
        assert client.post(BASE+'prepare',json=body).status_code == 503
        assert client.get('/api/health').status_code == 200
    finally:
        for _ in range(acquired): _SLOTS.release()
    assert client.post(BASE+'prepare',json=body).status_code == 200


def test_frozen_json_cannot_trigger_file_reads_or_unknown_shape(http):
    client, _, _ = http
    text = json.dumps({'frozen_hash':'a'*64, 'filename':'../../.env'})
    assert client.post(BASE+'calculate',json={'frozen_json':text, 'expected_frozen_hash':'a'*64}).status_code == 422

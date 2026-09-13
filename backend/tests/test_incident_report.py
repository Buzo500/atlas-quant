import importlib.util
import json
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'tools/diagnostics/incident_report.py'
spec = importlib.util.spec_from_file_location('incident_report', path)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def event(layer, name, **extra):
    return dict(diag=layer, event=name, correlation='client-1', **extra)


def test_success_is_not_an_incident():
    result = report.summarize([event('client', 'start'), event('client', 'body_end', ms=20)])
    assert result['correlated_requests'] == 1 and result['incidents'] == []
    assert result['root_cause_confirmed'] is False


def test_static_socket_failure_is_kept_without_misattributing_to_backend():
    result = report.summarize([
        event('client', 'start', path='/_next/static/chunks/app.js', resource_type='script'),
        event('client', 'failed', code='net::ERR_NO_BUFFER_SPACE', ms=24),
    ])
    incident = result['incidents'][0]
    assert incident['failed'] and not incident['slow']
    assert 'no demuestra' in incident['observation']
    assert incident['events'][0]['resource_type'] == 'script'
    assert result['root_cause_confirmed'] is False


def test_timeout_correlates_stages_without_claiming_root_cause_or_copying_secrets():
    result = report.summarize([event('client', 'start', body='private'), event('backend', 'body_end', ms=2),
        event('proxy', 'finish', ms=3, cookie='private'), event('client', 'failed', ms=10001)])
    value = result['incidents'][0]
    assert value['failed'] and value['slow']
    assert value['observation'].startswith('Proxy finalizado')
    assert 'private' not in json.dumps(result)
    assert not result['root_cause_confirmed']


def test_backend_incomplete_is_only_a_stage_observation():
    result = report.summarize([event('backend', 'start'), event('proxy', 'node_pending', ms=1200)])
    assert result['incidents'][0]['observation'].startswith('Petición recibida por ASGI')


def test_reader_extracts_only_trace_json_and_is_bounded(tmp_path):
    (tmp_path/'frontend.log').write_text('unstructured secret\n' + json.dumps(event('proxy', 'node_error', code='ECONNRESET'))+'\n', encoding='utf-8')
    result = report.write_report(tmp_path)
    assert len(result['incidents']) == 1
    assert 'secret' not in (tmp_path/'diagnostic-report.json').read_text(encoding='utf-8')
    assert result['logs_truncated'] is False


def test_server_diagnostic_retains_fatal_tail_but_not_descriptor_credentials(tmp_path):
    (tmp_path/'run.json').write_text(json.dumps(dict(token='private-token',
        server_exit_codes={'frontend': 1}, ownership_failure={'reason': 'child_exited'})))
    (tmp_path/'frontend.log').write_text('old line\n' * 4000 +
        json.dumps(event('proxy', 'start')) + '\nFATAL ERROR: controlled failure\n', encoding='utf-8')
    result = report.server_diagnostics(tmp_path)
    assert result['server_exit_codes'] == {'frontend': 1}
    assert result['ownership_failure']['reason'] == 'child_exited'
    assert 'private-token' not in json.dumps(result)
    tail = result['logs']['frontend.log']
    assert tail['truncated'] and len(tail['tail']) < 16384
    assert 'FATAL ERROR: controlled failure' in tail['tail']
    assert 'correlation' not in tail['tail']
    assert result['logs']['backend.log']['unavailable']


def test_server_diagnostic_survives_missing_descriptor(tmp_path):
    assert report.server_diagnostics(tmp_path)['descriptor_unavailable']


def test_server_log_tail_removes_query_values(tmp_path):
    (tmp_path/'backend.log').write_text('INFO: "GET /api/search?q=private-value HTTP/1.1" 200 OK\n')
    result = report.server_diagnostics(tmp_path)
    assert 'private-value' not in json.dumps(result)
    assert '/api/search?[redacted]' in result['logs']['backend.log']['tail']

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('tcp_capture', Path(__file__).resolve().parents[2] / 'tools/diagnostics/tcp_capture.py')
tcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tcp)


def test_aggregate_ipv4_ipv6_bound_pid_zero_and_no_remote_data():
    result = tcp.aggregate('''TCP 127.0.0.1:50001 198.51.100.1:443 ESTABLISHED 42
TCP 127.0.0.1:50001 127.0.0.1:8000 ESTABLISHED 42
TCP [::1]:50002 [::]:0 BOUND 43
TCP 0.0.0.0:50003 0.0.0.0:0 TIME_WAIT 0
TCP invalid:port remote BOUND 44
UDP 0.0.0.0:4 *:* 42''')
    assert result['sockets'] == 4 and result['malformed_rows'] == 1
    assert result['rows'][1]['distinct_local_ports'] == 1
    assert result['rows'][1]['sockets'] == 2
    assert result['rows'][0]['pid'] == 0
    assert result['rows'][2]['family'] == 6
    assert '198.51' not in json.dumps(result) and '50001' not in json.dumps(result)


def test_capture_stops_flushes_and_preserves_event_evidence(tmp_path):
    with tcp.Capture(tmp_path/'tcp.jsonl', interval=1, duration=2,
                     sample=lambda: dict(sockets=13, rows=[]),
                     events=lambda _: [dict(id=4231, record_id=10, utc='2026-09-13T00:00:00Z')]) as capture:
        pass
    rows = [json.loads(line) for line in capture.path.read_text(encoding='utf-8').splitlines()]
    assert not capture.thread.is_alive() and capture.error is None
    assert rows[-1]['stopped'] and rows[-1]['tcpip_events'][0]['id'] == 4231


def test_failed_sampler_is_explicit_and_does_not_break_shutdown(tmp_path):
    def failure():
        raise OSError('secret command')
    with tcp.Capture(tmp_path/'tcp.jsonl', interval=1, duration=1, sample=failure, events=lambda _: []) as capture:
        capture.thread.join(2)
    text = capture.path.read_text(encoding='utf-8')
    assert 'sample_unavailable' in text and 'secret' not in text


def test_summary_preserves_peak_pid_time_and_deduplicates_events(tmp_path):
    path=tmp_path/'capture.jsonl'
    row=dict(pid=42,state='BOUND',family=4,loopback=True,sockets=3,distinct_local_ports=3,process_name='node.exe')
    event=dict(id=4231,record_id=12,utc='2026-09-13T00:00:00Z')
    values=[dict(utc='first',sockets=3,rows=[row],tcpip_events=[event]),
            dict(utc='second',sockets=10,rows=[dict(row,sockets=10)],tcpip_events=[event])]
    path.write_text('\n'.join(json.dumps(v) for v in values),encoding='utf-8')
    result=tcp.summary(path)
    assert result['samples']==2 and result['top_peaks'][0]['utc']=='second'
    assert result['top_peaks'][0]['pid']==42 and result['tcpip_events']==[event]
    assert not result['root_cause_confirmed']


def test_byte_limit_stops_without_partial_json_or_exceeding_cap(tmp_path,monkeypatch):
    monkeypatch.setattr(tcp,'MAX_BYTES',600)
    with tcp.Capture(tmp_path/'bounded.jsonl',interval=1,duration=2,
                     sample=lambda:dict(extra='á'*1000),events=lambda _:[]) as capture:
        capture.thread.join(2)
    assert capture.error=='evidence_size_limit'
    assert capture.path.stat().st_size<=600
    assert b'\r\n' not in capture.path.read_bytes()
    for line in capture.path.read_text(encoding='utf-8').splitlines(): json.loads(line)

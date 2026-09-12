"""Correlate bounded, opt-in trace metadata; stage observations are not root causes."""
import json
from pathlib import Path

FIELDS = {'diag', 'event', 'utc', 'correlation', 'ms', 'method', 'path', 'status',
          'transport', 'complete', 'finished', 'code', 'sent', 'response_complete'}


def server_diagnostics(directory: Path):
    """Keep bounded server stderr evidence from this credential-free E2E run."""
    result = {'logs': {}}
    try:
        descriptor = json.loads((directory / 'run.json').read_text(encoding='utf-8'))
        result.update({key: descriptor.get(key) for key in
            ('ownership_failure', 'server_exit_codes', 'forced_stop')})
    except (OSError, ValueError):
        result['descriptor_unavailable'] = True
    for name in ('frontend.log', 'backend.log'):
        try:
            with (directory / name).open('rb') as stream:
                size = stream.seek(0, 2)
                start = max(0, size - 16384)
                stream.seek(start)
                raw = stream.read(16384)
            # Drop an incomplete first line and trace JSON (already in the report).
            lines = raw.decode('utf-8', errors='replace').splitlines()
            if start:
                lines = lines[1:]
            result['logs'][name] = dict(truncated=bool(start),
                tail='\n'.join(line for line in lines if '{"diag":' not in line))
        except OSError:
            result['logs'][name] = {'unavailable': True}
    return result


def summarize(events):
    groups = {}
    for event in events:
        ident = event.get('correlation')
        if ident:
            groups.setdefault(ident, []).append({k: v for k, v in event.items() if k in FIELDS})
    incidents = []
    for ident, items in groups.items():
        failed = any(e['event'] in ('failed', 'node_error', 'client_request_aborted') or
            (isinstance(e.get('status'), int) and e['status'] >= 500) or
            (e['event'] == 'close' and e.get('finished') is False) for e in items)
        slow = max((e.get('ms', 0) for e in items if isinstance(e.get('ms', 0), (int, float))), default=0) >= 1000
        if not (failed or slow):
            continue
        stages = {f"{e['diag']}:{e['event']}" for e in items}
        if any(e.get('code') == 'ECONNREFUSED' for e in items):
            observation = 'Conexión al backend rechazada (ECONNREFUSED); comprobar si el servidor había terminado de arrancar.'
        elif 'client:body_end' in stages:
            observation = 'El cliente completó el cuerpo; revisar tiempos/estado.'
        elif 'proxy:finish' in stages:
            observation = 'Proxy finalizado; falta finalización del cliente en la captura.'
        elif 'backend:body_end' in stages:
            observation = 'ASGI terminó el envío; falta finalización del proxy en la captura.'
        elif 'backend:start' in stages:
            observation = 'Petición recibida por ASGI; falta finalización del backend en la captura.'
        else:
            observation = 'No consta recepción ASGI correlacionada; captura insuficiente para localizar causa.'
        incidents.append(dict(correlation=ident, failed=failed, slow=slow, client_observed=any(e['diag']=='client' for e in items), observation=observation, events=items[:120], events_truncated=len(items)>120))
    return dict(correlated_requests=len(groups), incidents=incidents[:100], incidents_truncated=len(incidents)>100,
                root_cause_confirmed=False)


def write_report(directory: Path):
    events, truncated = [], False
    for name in ('backend.log', 'frontend.log', 'playwright.log'):
        path = directory / name
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            raw = stream.read(32 * 1024 * 1024 + 1)
        truncated |= len(raw) > 32 * 1024 * 1024
        for line in raw[:32 * 1024 * 1024].decode('utf-8', errors='replace').splitlines():
            start = line.find('{"diag":')
            if start < 0 or len(line) > 20_000:
                continue
            try:
                value = json.loads(line[start:])
                if value.get('diag') in ('proxy', 'backend', 'client') and isinstance(value.get('event'), str):
                    events.append(value)
            except (ValueError, AttributeError):
                continue
    result = dict(**summarize(events), logs_truncated=truncated,
                  scope='E2E aislado; umbral de captura 1 s; no cambia timeouts ni reintenta operaciones.')
    (directory/'diagnostic-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result

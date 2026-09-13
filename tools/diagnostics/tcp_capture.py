"""Bounded Windows socket pressure evidence. Read-only, no addresses or command lines."""
import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

MAX_BYTES = 8_000_000


def aggregate(text):
    """Keep counts/PIDs only; TIME_WAIT/PID 0 cannot identify its former owner."""
    counts, ports = Counter(), {}
    malformed = 0
    for line in text.splitlines():
        fields = line.split()
        if not fields or fields[0] != 'TCP':
            continue
        if len(fields) != 5 or not fields[-1].isdigit():
            malformed += 1
            continue
        try:
            address, port = fields[1].rsplit(':', 1)
            address = ipaddress.ip_address(address.strip('[]').split('%')[0])
            port = int(port)
            if not 0 <= port <= 65535 or not re.fullmatch('[A-Z_]+', fields[3]):
                raise ValueError('invalid row')
        except ValueError:
            malformed += 1
            continue
        key = (int(fields[4]), fields[3], address.version, address.is_loopback)
        counts[key] += 1
        ports.setdefault(key, set()).add(port)
    return dict(rows=[dict(pid=k[0], state=k[1], family=k[2], loopback=k[3],
                          sockets=v, distinct_local_ports=len(ports[k]))
                     for k, v in sorted(counts.items())], malformed_rows=malformed,
                sockets=sum(counts.values()))


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, errors='replace',
        timeout=4, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode:
        raise OSError('TCP observation unavailable')
    return result.stdout


def events_since(start):
    # start is generated internally as an ISO UTC timestamp, never supplied script text.
    script = ("$e = @(Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='Tcpip';"
        "Id=4227,4231;StartTime=[datetime]'" + start + "'} -MaxEvents 32 -ErrorAction SilentlyContinue);"
        "ConvertTo-Json -Compress -InputObject @($e | ForEach-Object {"
        "@{id=$_.Id;record_id=$_.RecordId;utc=$_.TimeCreated.ToUniversalTime().ToString('o')}})")
    values = json.loads(command(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script]) or '[]')
    return [dict(id=v['id'], record_id=v['record_id'], utc=v['utc']) for v in values]


def windows_sample():
    result = aggregate(command(['netstat.exe', '-anoq']))
    try:
        names = {int(r[1]):r[0][:128] for r in csv.reader(command(['tasklist.exe','/FO','CSV','/NH']).splitlines())
                 if len(r)>=2 and r[1].isdigit() and not any(ord(c)<32 for c in r[0])}
        for row in result['rows']:
            row['process_name'] = names.get(row['pid']) if row['pid'] else None
        result['process_identity_note'] = 'Nombre observado después de netstat; PID puede reciclarse, no prueba de propietario histórico.'
    except (OSError, ValueError, subprocess.SubprocessError):
        result['process_names_unavailable'] = True
    return result


def summary(path):
    """Small CI evidence survives ephemeral runner cleanup; full samples stay local."""
    peaks, events, count, unavailable, overall = {}, {}, 0, 0, None
    with Path(path).open('rb') as stream:
        raw=stream.read(8_100_000)
    for line in raw.decode('utf-8').splitlines():
        value=json.loads(line)
        if 'sockets' in value:
            count+=1
            if overall is None or value['sockets']>overall['sockets']:
                overall=dict(utc=value['utc'],sockets=value['sockets'])
            for row in value.get('rows',[]):
                key=(row['pid'],row['state'],row['family'],row['loopback'])
                if key not in peaks or row['sockets']>peaks[key]['sockets']:
                    peaks[key]=dict(utc=value['utc'],**row)
        unavailable+=bool(value.get('sample_unavailable'))
        for event in value.get('tcpip_events') or []:
            events[event['record_id']]=event
    return dict(samples=count,unavailable_samples=unavailable,peak=overall,
        top_peaks=sorted(peaks.values(),key=lambda r:r['sockets'],reverse=True)[:20],
        tcpip_events=list(events.values()),root_cause_confirmed=False,
        note='Muestreo periódico; correlación temporal y recuentos no acreditan causalidad. PID 0 no identifica consumidor.')


class Capture:
    def __init__(self, path, *, interval=5, duration=3600, sample=None, events=None):
        if not 1 <= interval <= 60 or not 1 <= duration <= 3600:
            raise ValueError('Captura: intervalo 1–60 s, duración máxima 3600 s.')
        self.path, self.interval, self.duration = Path(path), interval, duration
        self.sample = sample or windows_sample
        self.events = events or events_since
        self.stop = threading.Event()
        self.started = datetime.now(timezone.utc).isoformat()
        self.error = None
        self.size_limited = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open('x', encoding='utf-8', newline='\n')
        self.thread = threading.Thread(target=self._run, name='atlas-tcp-evidence', daemon=True)
        self.thread.start()
        return self

    def _write(self, value):
        line = json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n'
        if self.stream.tell() + len(line.encode('utf-8')) > MAX_BYTES:
            self.size_limited = True
            self.error = 'evidence_size_limit'
            return
        self.stream.write(line)
        self.stream.flush()

    def _run(self):
        started = time.monotonic()
        count = 0
        try:
            self._write(dict(format='atlas-tcp-pressure-v1', started_at=self.started,
                interval_seconds=self.interval, max_seconds=self.duration,
                note='PID 0/TIME_WAIT no identifica al consumidor original; sin direcciones ni rutas.'))
            while time.monotonic() - started < self.duration and not self.size_limited:
                observation = dict(utc=datetime.now(timezone.utc).isoformat())
                try:
                    observation.update(self.sample())
                except (OSError, ValueError, subprocess.SubprocessError):
                    observation['sample_unavailable'] = True
                if count % 3 == 0 or self.stop.is_set():
                    try:
                        observation['tcpip_events'] = self.events(self.started)
                    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                        observation['events_unavailable'] = True
                self._write(observation)
                count += 1
                if self.size_limited or self.stop.wait(self.interval):
                    break
            try:
                final_events = self.events(self.started)
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                final_events = None
            self._write(dict(finished_at=datetime.now(timezone.utc).isoformat(), samples=count,
                stopped=self.stop.is_set(), bounded_stop=not self.stop.is_set(), tcpip_events=final_events))
        except Exception as exc:
            self.error = type(exc).__name__
        finally:
            self.stream.close()

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=20)
        if self.thread.is_alive():
            self.error = 'capture_stop_timeout'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=900)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Captura disponible en Windows.')
    with Capture(args.output, duration=args.seconds) as capture:
        try:
            capture.thread.join(args.seconds + 12)
        except KeyboardInterrupt:
            pass
    print(json.dumps(dict(output=str(args.output), error=capture.error)))


if __name__ == '__main__':
    main()

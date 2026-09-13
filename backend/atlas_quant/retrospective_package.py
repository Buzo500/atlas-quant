"""Portable retrospective reports shared by CLI and HTTP, without database writes."""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from .quality import digest
from .retrospective import POLICY, evaluate, prices_csv

ROOT = Path(__file__).resolve().parents[2]

FORMAT = 'atlas-research-development-bundle-v1'
LIMIT = 20_000_000
MEMBERS = {'report.json', 'prices.csv', 'nav.csv', 'metrics.csv', 'trades.csv', 'README.txt', 'manifest.json'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def read_json(path):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT+1)
    if len(raw) > LIMIT:
        raise ValueError('Fichero demasiado grande.')
    return json.loads(raw)


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def code_hashes():
    paths = sorted((ROOT/'backend/atlas_quant').glob('*.py')) + [ROOT/'tools/run_retrospective.py']
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in paths}


def run(frozen):
    result = evaluate(frozen)
    payload = dict(format=FORMAT, frozen=frozen, result=result, code_sha256=code_hashes())
    return dict(**payload, report_hash=digest(payload))


def verify_report(report, *, allow_code_change=False):
    if not isinstance(report, dict) or report.get('format') != FORMAT:
        raise ValueError('Formato de informe desconocido.')
    code = report.get('code_sha256')
    if not isinstance(code, dict) or not code or any(not isinstance(k, str) or not isinstance(v, str)
            or not re.fullmatch('[0-9a-f]{64}', v) for k, v in code.items()):
        raise ValueError('Huellas de código inválidas.')
    if not allow_code_change and code != code_hashes():
        raise ValueError('Código distinto; usa la revisión original para una reproducción con el mismo código.')
    result = evaluate(report['frozen'])
    payload = dict(format=FORMAT, frozen=report['frozen'], result=result, code_sha256=code)
    if report != dict(**payload, report_hash=digest(payload)):
        raise ValueError('El cálculo no reproduce el informe guardado.')
    return report


def table(rows, fields):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def bundle_files(report):
    result = report['result']['development']
    files = {
        'report.json': encoded(report),
        'prices.csv': prices_csv(report['frozen']['rows']).encode('utf-8'),
        'nav.csv': table(result['curve'], ['date', 'sma_eur', 'buy_hold_eur', 'cash_eur']),
        'metrics.csv': table(result['metrics'], ['name', 'final_nav_eur', 'return_pct', 'max_drawdown_pct', 'fills', 'fees_eur']),
        'trades.csv': table(result['trades'], ['strategy', 'side', 'date', 'quantity', 'price_eur', 'fee_eur']),
        'README.txt': ('ATLAS Quant · Investigación retrospectiva\n'
            'Solo desarrollo; la reserva no se calcula ni contiene precios en este paquete.\n'
            'JSON conserva configuración, fechas, procedencia, supuestos y huellas de código.\n'
            'Comprobar con tools/run_retrospective.py verify paquete.zip usando el mismo código.\n'
            'Los hashes comprueban integridad, no autenticidad del proveedor.\n\n'
            + '\n'.join(report['result']['warnings'])+'\n').encode('utf-8'),
    }
    manifest = dict(format=FORMAT, policy=POLICY, report_hash=report['report_hash'],
        files={name:dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)) for name,data in files.items()})
    return {**files, 'manifest.json':encoded(manifest)}


def export_bytes(report, *, allow_code_change=False):
    files = bundle_files(verify_report(report, allow_code_change=allow_code_change))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[name])
    return buffer.getvalue()


def export(report, path):
    write_new(path, export_bytes(report))


def verify_bundle(path):
    if path.stat().st_size > LIMIT:
        raise ValueError('Paquete demasiado grande.')
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) != len(MEMBERS) or {i.filename for i in members} != MEMBERS:
            raise ValueError('Paquete con rutas, miembros duplicados o archivos inesperados.')
        if sum(i.file_size for i in members) > LIMIT or any(i.flag_bits & 1 for i in members):
            raise ValueError('Contenido excesivo o cifrado no admitido.')
        files = {i.filename:archive.read(i) for i in members}
    report = json.loads(files['report.json'])
    # Recompute every derived CSV and the manifest, not just self-reported hashes.
    if files != bundle_files(verify_report(report)):
        raise ValueError('Manifiesto, CSV o informe incoherentes.')
    return report

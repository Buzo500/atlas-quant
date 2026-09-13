"""Local retrospective research: freeze, run, export and independently reproduce.

No database, server, credentials or network. Never calculates the held-out period.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from atlas_quant.quality import digest
from atlas_quant.retrospective import POLICY, RetrospectiveRequest, evaluate, freeze, prices_csv

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
    paths = sorted((ROOT/'backend/atlas_quant').glob('*.py')) + [Path(__file__)]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            for p in paths}


def run(frozen):
    result = evaluate(frozen)
    payload = dict(format=FORMAT, frozen=frozen, result=result, code_sha256=code_hashes())
    return dict(**payload, report_hash=digest(payload))


def verify_report(report):
    if not isinstance(report, dict) or report.get('format') != FORMAT or report.get('code_sha256') != code_hashes():
        raise ValueError('Formato o código distintos; no se afirma reproducción.')
    if report != run(report['frozen']):
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


def export(report, path):
    files = bundle_files(verify_report(report))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, files[name])
    write_new(path, buffer.getvalue())


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    prepare = actions.add_parser('freeze')
    prepare.add_argument('--request', type=Path, required=True)
    prepare.add_argument('--prices', type=Path, required=True)
    prepare.add_argument('--output', type=Path, required=True)
    execute = actions.add_parser('run')
    execute.add_argument('input', type=Path)
    execute.add_argument('--output', type=Path, required=True)
    pack = actions.add_parser('export')
    pack.add_argument('input', type=Path)
    pack.add_argument('--output', type=Path, required=True)
    verify = actions.add_parser('verify')
    verify.add_argument('input', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'freeze':
            request = RetrospectiveRequest.model_validate_json(encoded(read_json(args.request)))
            with args.prices.open('rb') as stream:
                prices = stream.read(2_000_001)
            result = freeze(request, prices.decode('utf-8'))
            write_new(args.output, encoded(result))
        elif args.action == 'run':
            result = run(read_json(args.input))
            write_new(args.output, encoded(result))
        elif args.action == 'export':
            export(read_json(args.input), args.output)
        else:
            result = verify_bundle(args.input)
            print(json.dumps(dict(reproduced=True, report_hash=result['report_hash'], holdout_evaluated=False)))
        if args.action != 'verify':
            print(json.dumps(dict(output=str(args.output), action=args.action, holdout_evaluated=False)))
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'No se pudo completar la investigación: {exc}\n')


if __name__ == '__main__':
    main()

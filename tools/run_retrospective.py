"""Local retrospective research: freeze, run, export and reproduce; no held-out calculation."""
import argparse
from pathlib import Path
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
from atlas_quant.retrospective import RetrospectiveRequest, freeze
# Re-exports keep the dev.6 Python entry points available for existing callers.
from atlas_quant.retrospective_package import (
    FORMAT, LIMIT, MEMBERS, encoded, read_json, write_new, code_hashes, run,
    verify_report, table, bundle_files, export, verify_bundle,
)


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

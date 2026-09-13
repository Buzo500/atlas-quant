"""Compile an unaltered ATLAS D7 LaTeX bundle locally, never arbitrary TeX."""
import argparse
import hashlib
import io
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from atlas_quant.period_latex import LIMIT, verify_archive
from atlas_quant.retrospective_package import encoded, write_new
from export_research_latex import compile_generated, engine_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='PDF nuevo; conserva el ZIP original.')
    args = parser.parse_args()
    try:
        if args.output.suffix.lower() != '.pdf' or any(args.output.with_suffix(s).exists() for s in ('.pdf','.log','.build.json')):
            raise ValueError('Elige un PDF nuevo y salidas sin archivos previos.')
        with args.input.open('rb') as stream:
            data = stream.read(LIMIT + 1)
        manifest = verify_archive(data)
        with zipfile.ZipFile(io.BytesIO(data)) as zipped:
            files = {name:zipped.read(name) for name in ('report.tex','atlas-style.tex','nav-plot.csv')}
        pdf, log, build = compile_generated(files, engine_path())
        write_new(args.output, pdf)
        write_new(args.output.with_suffix('.log'), log)
        build.update(zip_sha256=hashlib.sha256(data).hexdigest(), pdf_sha256=hashlib.sha256(pdf).hexdigest(),
                     manifest_hash=manifest['manifest_hash'])
        write_new(args.output.with_suffix('.build.json'), encoded(build))
        print(encoded(dict(pdf=str(args.output), source_modified=False)).decode('utf-8'))
    except (ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'No se pudo compilar el informe de cartera: {exc}\n')


if __name__ == '__main__':
    main()

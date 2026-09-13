"""Export verified retrospective JSON to editable LaTeX, with optional local PDF."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from atlas_quant.research_latex import archive, make_files, verify_archive
from atlas_quant.retrospective_package import encoded, read_json, write_new
from process_group import ProcessGroup

FLAGS = ['--nosocket', '--no-shell-escape', '--interaction=nonstopmode', '--halt-on-error']
MAX_OUTPUT = 32_000_000


def engine_path():
    local = ROOT / 'var/tools/tinytex-2026.09/TinyTeX/bin/windows/lualatex.exe'
    found = local if local.is_file() else shutil.which('lualatex')
    if not found:
        raise ValueError('LuaLaTeX no está instalado. El ZIP de fuentes ya está guardado; consulta docs/informes_latex_implementacion.md.')
    return str(Path(found).resolve())


def compile_generated(files, engine, *, timeout=120):
    """Internal generated assets only. This function never accepts an external TeX path."""
    scratch = ROOT / 'output/tmp'
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, openin_any='p', openout_any='p')
    # Fixed assets contain no user commands. Disable Lua sockets and external shell commands;
    # this is process containment, not an OS network/filesystem security sandbox.
    version = subprocess.run([engine, '--version'], capture_output=True, text=True,
                             timeout=10, check=True, env=env).stdout.splitlines()[0]
    if 'LuaHBTeX' not in version or 'TeX Live 2026' not in version:
        raise ValueError('La compilación PDF requiere LuaHBTeX de TeX Live 2026.')
    with tempfile.TemporaryDirectory(prefix='atlas-latex-', dir=scratch) as temporary:
        folder = Path(temporary)
        for name in ('report.tex', 'atlas-style.tex', 'nav-plot.csv'):
            (folder / name).write_bytes(files[name])
        deadline = time.monotonic() + timeout
        with ProcessGroup(memory_limit_bytes=2_147_483_648) as group:
            for turn in (1, 2):
                output = folder / f'pass-{turn}.txt'
                with output.open('wb') as log:
                    process = subprocess.Popen([engine, *FLAGS, 'report.tex'], cwd=folder,
                        env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                    try:
                        group.add(process)
                    except BaseException:
                        process.kill()
                        process.wait(timeout=8)
                        raise
                    while process.poll() is None:
                        if time.monotonic() >= deadline:
                            raise ValueError('La compilación superó 120 segundos; el ZIP de fuentes se conserva.')
                        if sum(p.stat().st_size for p in folder.iterdir() if p.is_file()) > MAX_OUTPUT:
                            raise ValueError('La compilación superó el límite de salida; el ZIP de fuentes se conserva.')
                        time.sleep(.1)
                if process.returncode:
                    raise ValueError('LuaLaTeX no pudo compilar la fuente generada: ' +
                                     output.read_text(encoding='utf-8', errors='replace')[-2400:])
        pdf = (folder / 'report.pdf').read_bytes()
        log = (folder / 'report.log').read_bytes()
        if not pdf.startswith(b'%PDF-') or len(pdf) > MAX_OUTPUT:
            raise ValueError('Salida PDF inválida o demasiado grande.')
        return pdf, log, dict(engine=version, flags=FLAGS, passes=2, sockets=False, shell_escape=False,
                              timeout_seconds=timeout, memory_limit_bytes=2_147_483_648)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Informe JSON verificado; nunca un archivo TeX.')
    parser.add_argument('--output', type=Path, required=True, help='ZIP nuevo de fuente y datos.')
    parser.add_argument('--pdf', action='store_true', help='Compilar localmente y guardar PDF/log/recibo junto al ZIP.')
    args = parser.parse_args()
    try:
        if args.output.suffix.lower() != '.zip':
            raise ValueError('La salida debe terminar en .zip.')
        targets = [args.output]
        if args.pdf:
            targets += [args.output.with_suffix(s) for s in ('.pdf', '.log', '.build.json')]
        if any(p.exists() for p in targets):
            raise ValueError('No se sobrescriben archivos existentes; elige otra salida.')
        files = make_files(read_json(args.input))
        zipped = archive(files)
        verify_archive(zipped)
        write_new(args.output, zipped)
        if args.pdf:
            pdf, log, build = compile_generated(files, engine_path())
            write_new(args.output.with_suffix('.pdf'), pdf)
            write_new(args.output.with_suffix('.log'), log)
            build.update(zip_sha256=hashlib.sha256(zipped).hexdigest(), pdf_sha256=hashlib.sha256(pdf).hexdigest(),
                         manifest_sha256=hashlib.sha256(files['manifest.json']).hexdigest())
            write_new(args.output.with_suffix('.build.json'), encoded(build))
        print(encoded(dict(source=str(args.output), pdf=args.pdf, holdout_evaluated=False)).decode('utf-8'))
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'No se pudo completar la exportación: {exc}\n')


if __name__ == '__main__':
    main()

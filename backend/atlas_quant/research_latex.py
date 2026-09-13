"""Editable LaTeX for the complete verified development; no engine or filesystem inputs."""
from datetime import datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import hashlib
import io
import json
from pathlib import Path
import textwrap
import unicodedata
import zipfile

from . import __version__
from .quality import digest
from .retrospective_package import bundle_files, code_hashes, encoded, table, verify_report

FORMAT = 'atlas-research-latex-bundle-v1'
TEMPLATE = 'atlas-report-template-v1'
STYLE = Path(__file__).with_name('atlas-report-style.tex')
SPECIAL = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '%': r'\%', '$': r'\$',
           '#': r'\#', '_': r'\_', '&': r'\&', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}


def tex_text(value):
    """Characters are escaped individually; generated commands are never escaped twice."""
    text = str(value)
    if any(unicodedata.category(c).startswith('C') and c not in '\n\r\t' for c in text):
        raise ValueError('El informe contiene caracteres de control no imprimibles.')
    text = ' '.join(text.split())
    return ' '.join((r'\allowbreak{}'.join(SPECIAL.get(c, c) for c in word)
                     if len(word) > 32 else ''.join(SPECIAL.get(c, c) for c in word))
                    for word in text.split(' '))


def identifier(value):
    # Allow line breaks without using verbatim/url or interpolating macro arguments.
    escaped = [tex_text(c) for c in str(value)]
    return r'\texttt{' + r'\allowbreak{}'.join(escaped) + '}'


def number(value, places=2):
    with localcontext() as ctx:
        ctx.prec = 96
        result = format(Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN), f',.{places}f')
    return result.replace(',', '\0').replace('.', ',').replace('\0', '.')


def short_date(value):
    return datetime.strptime(value, '%Y-%m-%d').strftime('%d/%m/%Y')


def row(*cells):
    return ' & '.join(cells) + r'\\' + '\n'


def context_table(entries):
    result = [r'\begin{longtable}{@{}>{\raggedright\arraybackslash}p{.25\linewidth}>{\raggedright\arraybackslash}p{.69\linewidth}@{}}',
              r'\toprule Campo & Valor\\\midrule\endfirsthead',
              r'\toprule Campo & Valor (continuación)\\\midrule\endhead']
    result.extend(row(tex_text(k), v) for k, v in entries)
    result.append(r'\bottomrule\end{longtable}')
    return '\n'.join(result)


def provenance_rows(request):
    # A longtable can split between rows, not inside a cell. Bound each paragraph
    # while retaining every word of the source and the complete original JSON.
    rows = []
    for label, key in [('Precios', 'provider'), ('Calendario', 'calendar_source'), ('Eventos', 'event_review')]:
        for index, part in enumerate(textwrap.wrap(request[key], width=500, break_long_words=True, break_on_hyphens=False)):
            rows.append((label if not index else label + ' (continuación)', tex_text(part)))
    return rows


def render(report, generated_at):
    request = report['frozen']['request']
    development = report['result']['development']
    config = request['config']
    curve = development['curve']
    matches = report['code_sha256'] == code_hashes()
    ticks = sorted({0, (len(curve) - 1) // 2, len(curve) - 1})
    width = '.84' if any(Decimal(p[key]) >= 100000 for p in curve for key in ('sma_eur', 'buy_hold_eur')) else '.94'
    # Coordinates contain validated decimal numbers only. Full precision remains in nav.csv.
    plot = [dict(session=i, sma_eur=p['sma_eur'], buy_hold_eur=p['buy_hold_eur']) for i,p in enumerate(curve)]
    parts = [r'\input{atlas-style.tex}', r'\begin{document}',
        r'{\small\bfseries\color{copper}INFORME DE DESARROLLO}\par',
        r'{\LARGE\bfseries ' + tex_text(request['symbol']) + r' · SMA ' + f"{request['fast']}/{request['slow']}" + r'}\par',
        tex_text(short_date(development['start_date']) + ' - ' + short_date(development['end_date'])) +
            r'\hfill EUR · ' + str(development['sessions']) + r' sesiones\par',
        r'\AtlasNote{\textbf{Investigación retrospectiva.} Disponibilidad, base de precios y ejecución supuestas. '
        r'No acredita la estrategia ni autoriza operaciones. La reserva no se calcula ni se incluye con precios.}',
        r'\AtlasSection{Resumen del periodo}', r'\begin{tabularx}{\linewidth}{@{}Xrrr@{}}',
        r'\toprule Referencia & NAV final EUR & Rentabilidad & Caída máx.\\\midrule']
    for metric in development['metrics']:
        parts.append(row(tex_text(metric['name']), number(metric['final_nav_eur']),
                         number(metric['return_pct']) + r'\,\%', number(metric['max_drawdown_pct']) + r'\,\%'))
    parts.extend([r'\bottomrule\end{tabularx}', r'\par\smallskip{\footnotesize ' + tex_text(' · '.join(
        f"{m['name']}: ejecuciones {m['fills']}; {number(m['fees_eur'])} EUR en comisiones"
        for m in development['metrics'][:2])) + r'}\par', r'\AtlasSection{Evolución del patrimonio}',
        r'\begin{tikzpicture}\begin{axis}[width=' + width + r'\linewidth,height=64mm,axis lines=left,',
        r'axis line style={rulegray},tick style={rulegray},grid=major,grid style={rulegray!50},',
        r'tick label style={font=\small\sffamily},scaled y ticks=false,',
        r'yticklabel={\pgfmathprintnumber[fixed,precision=0,1000 sep={.},dec sep={,},assume math mode=true]{\tick}},',
        'xtick={' + ','.join(str(v) for v in ticks) + '},',
        'xticklabels={' + ','.join(short_date(curve[v]['date']) for v in ticks) + '},',
        r'legend style={draw=none,font=\small,at={(0.5,1.08)},anchor=south,legend columns=2}]',
        r'\addplot[color=slate,thick] table[x=session,y=sma_eur,col sep=comma]{nav-plot.csv};',
        r'\addlegendentry{SMA}',
        r'\addplot[color=ink,dashed] table[x=session,y=buy_hold_eur,col sep=comma]{nav-plot.csv};',
        r'\addlegendentry{Comprar/mantener}', r'\end{axis}\end{tikzpicture}\par',
        r'{\footnotesize EUR. Eje horizontal por sesiones, no por distancia temporal. Eje vertical recortado '
        r'para mostrar la variación. Se incluyen todos los puntos del desarrollo.}\par',
        r'\AtlasSection{Lectura y límites}',
        tex_text('Capital inicial: ' + number(config['initial_cash_eur']) + ' EUR. La posición final se valora sin '
            'venta automática. La rentabilidad y la caída máxima corresponden al desarrollo completo, incluidos costes.'),
        tex_text(f"{development['rejected']} intentos rechazados y {development['expired']} oportunidades caducadas.")
            if 'rejected' in development else '',
        r'\par El rendimiento observado no implica rentabilidad futura. Comparar con comprar/mantener no '
        r'elimina sesgos de selección ni acredita significancia estadística.',
        r'\newpage\AtlasSection{Condiciones del cálculo}'])
    parts.append(context_table([
        ('Instrumento', identifier(request['instrument_id'])), ('Mercado / moneda', tex_text(request['market'] + ' / EUR')),
        ('Medias / capital', tex_text(f"SMA {request['fast']}/{request['slow']} · {number(config['initial_cash_eur'])} EUR")),
        ('Peso / límite / lote', tex_text(f"{config['strategy_weight']} / {config['max_position_weight']} / {config['quantity_step']}")),
        ('Compras', 'Habilitadas' if config['purchases_enabled'] else 'Bloqueadas'),
        ('Comisión', tex_text(number(config['fixed_fee_eur']) + ' EUR + ' + config['fee_bps'] + ' pb')),
        ('Deslizamiento', tex_text(config['slippage_bps'] + ' pb')),
        ('Horarios supuestos', 'Europe/Berlin: apertura 09:00, cierre 17:30 (14:00 abreviada), decisión 18:00.'),
        ('Tramo del informe', tex_text(short_date(development['start_date']) + ' - ' + short_date(development['end_date']) + ', inclusivo')),
        ('Reserva sin calcular', tex_text(short_date(report['frozen']['holdout']['start']) + ' - ' + short_date(report['frozen']['holdout']['end']) + '; ' + str(report['frozen']['holdout']['sessions']) + ' sesiones')),
    ]))
    parts.extend([r'\AtlasSection{Procedencia y supuestos}', context_table(provenance_rows(request)), r'\begin{itemize}'])
    parts.extend(r'\item ' + tex_text(w) for w in report['result']['warnings'])
    parts.extend([r'\end{itemize}', r'\clearpage\AtlasSection{Ejecuciones simuladas}',
        r'{\small\begin{longtable}{@{}>{\raggedright\arraybackslash}p{.28\linewidth}lrrr@{}}',
        r'\toprule Estrategia / lado & Fecha & Cantidad & Precio EUR & Comisión EUR\\\midrule\endfirsthead',
        r'\toprule Estrategia / lado & Fecha & Cantidad & Precio EUR & Comisión EUR\\\midrule\endhead'])
    for trade in development['trades']:
        label = ('SMA' if trade['strategy'] == 'SMA' else 'Comprar/mantener') + (' · compra' if trade['side'] == 'buy' else ' · venta')
        parts.append(row(tex_text(label), short_date(trade['date']), tex_text(trade['quantity']), number(trade['price_eur'], 4), number(trade['fee_eur'])))
    if not development['trades']:
        parts.append(r'\multicolumn{5}{l}{Sin ejecuciones simuladas en el periodo.}\\')
    parts.extend([r'\bottomrule\end{longtable}}',
        r'\AtlasSection{Reproducción y trazabilidad}',
        context_table([
            ('Generado UTC', tex_text(generated_at)), ('ATLAS / plantilla', tex_text(__version__) + r' / ' + identifier(TEMPLATE)),
            ('Política de investigación', identifier(report['result']['policy'])),
            ('Informe original', identifier(report['report_hash'])), ('Protocolo', identifier(report['frozen']['frozen_hash'])),
            ('CSV original', identifier(request['source_sha256'])),
            ('Código del cálculo', 'Coincide con las huellas del informe.' if matches else 'Los resultados se reproducen, pero el código ha cambiado. Se conservan las huellas originales.'),
        ]), r'JSON/CSV conservan precisión completa. Las cifras impresas se redondean solo para presentación. '
        r'El manifiesto enlaza cada archivo mediante SHA-256; comprueba integridad, no autenticidad del proveedor. '
        r'Los archivos del paquete permiten editar y volver a compilar el documento.', r'\end{document}'])
    return '\n'.join(parts).encode('utf-8'), table(plot, ['session', 'sma_eur', 'buy_hold_eur'])


def make_files(report, *, generated_at=None):
    report = verify_report(report, allow_code_change=True)
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('La generación debe identificarse en UTC.')
    source, plot = render(report, timestamp)
    original = bundle_files(report)
    files = {k: v for k,v in original.items() if k not in ('README.txt', 'manifest.json')}
    files.update({'research-manifest.json': original['manifest.json'], 'research-README.txt': original['README.txt'],
                  'report.tex': source, 'atlas-style.tex': STYLE.read_bytes().replace(b'\r\n', b'\n'), 'nav-plot.csv': plot,
                  'README.txt': ('ATLAS Quant · Fuente LaTeX del desarrollo retrospectivo\n'
                    'report.json y CSV conservan el informe original. La reserva no contiene precios.\n'
                    'Compilar la fuente generada con LuaLaTeX/TeX Live 2026, dos pasadas:\n'
                    'lualatex --nosocket --no-shell-escape --halt-on-error --interaction=nonstopmode report.tex\n'
                    'No compilar archivos TeX externos o alterados como si estuvieran verificados.\n'
                    'Paquetes: fontspec, babel/spanish, geometry, xcolor, booktabs, tabularx, longtable, fancyhdr, hyperref, pgfplots.\n'
                    'Fuentes: TeX Gyre Heros y Latin Modern Mono. Recursos locales; no requiere IA o red.\n').encode('utf-8')})
    manifest = dict(format=FORMAT, template=TEMPLATE, source_report_hash=report['report_hash'], generated_at=timestamp,
        atlas_version=__version__, code_matches=report['code_sha256'] == code_hashes(),
        renderer_sha256=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
        files={name:dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)) for name,data in files.items()})
    files['manifest.json'] = encoded(dict(**manifest, manifest_hash=digest(manifest)))
    return files


def archive(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zipped:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zipped.writestr(info, value)
    return buffer.getvalue()


def export_latex(report):
    return archive(make_files(report))


def verify_archive(data):
    """Rebuild fixed sources and all hashes; never extract or execute archive entries."""
    if len(data) > 32_000_000:
        raise ValueError('Paquete LaTeX demasiado grande.')
    with zipfile.ZipFile(io.BytesIO(data)) as zipped:
        entries = zipped.infolist()
        if len(entries) != 12 or len({e.filename for e in entries}) != len(entries) or sum(e.file_size for e in entries) > 32_000_000:
            raise ValueError('Contenido del paquete LaTeX inválido.')
        supplied = {e.filename: zipped.read(e) for e in entries}
    try:
        manifest = json.loads(supplied['manifest.json'])
        expected = make_files(json.loads(supplied['report.json']), generated_at=manifest['generated_at'])
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Manifiesto LaTeX inválido.') from exc
    if supplied != expected:
        raise ValueError('La fuente o el manifiesto no coinciden con el informe y el generador actual.')
    return manifest

"""Editable, bounded D7 export using the accepted ATLAS style; no live book reads."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import zipfile
from . import __version__
from .period_report import adapt
from .performance_contracts import PerformancePoint, CostItem
from .valuation_contracts import ExternalFlow
from .quality import digest
from .research_latex import STYLE, TEMPLATE, archive, context_table, identifier, number, row, short_date, tex_text
from .retrospective_package import encoded, table

FORMAT = 'atlas-period-latex-bundle-v1'
MEMBERS = {'source-report.json', 'period-report.json', 'curve.csv', 'flows.csv', 'costs.csv',
           'report.tex', 'atlas-style.tex', 'nav-plot.csv', 'manifest.json', 'README.txt'}
LIMIT = 32_000_000
STATUS = {'complete':'Completo', 'provisional':'Provisional', 'incomplete':'Incompleto', 'unavailable':'No disponible'}
REASONS = {'missing_fx':'Falta un tipo de cambio necesario para valorar en EUR.',
    'missing_price':'Falta un precio necesario para valorar la cartera.',
    'discontinuous_nav':'El patrimonio no tiene una base positiva y continua en todos los tramos.',
    'out_of_domain':'La tasa anual queda fuera del dominio de búsqueda del cálculo D7.',
    'no_investment':'No hay inversión y recuperación de capital con signos opuestos.',
    'missing_flow_fx':'Falta FX para un flujo externo del periodo.',
    'missing_cost_fx':'Falta FX para un coste del periodo.',
    'unlinked_dividend_history':'Hay cobros sin derecho histórico acreditado.',
    'numeric_range':'La métrica supera el rango numérico admitido.'}


def amount(value, *, rate=False):
    if value is None:
        return 'No disponible'
    display = Decimal(value) * (100 if rate else 1)
    if abs(display) < Decimal('.005'):
        display = Decimal(0)
    return number(display) + (r'\,\%' if rate else '')


def rows_csv(rows):
    return [{k:encoded(v).decode('utf-8') if isinstance(v, (dict, list)) else v for k,v in r.items()} for r in rows]


def long_table(headers, widths, rows):
    spec = '@{}' + ''.join(r'>{\raggedright\arraybackslash}p{' + str(w) + r'\linewidth}' for w in widths) + '@{}'
    header = row(*(tex_text(h) for h in headers))
    return '\n'.join([r'{\footnotesize\begin{longtable}{' + spec + '}',
        r'\toprule ' + header + r'\midrule\endfirsthead',
        r'\toprule ' + header + r'\midrule\endhead',
        *(row(*r) for r in rows), r'\bottomrule\end{longtable}}'])


def render(model, generated_at, current):
    m = model.model_dump(mode='json')
    parts = [r'\input{atlas-style.tex}',
        r'\hypersetup{pdftitle={ATLAS Quant: informe de cartera}}',
        r'\fancyhead[L]{\small\textbf{ATLAS}\quad Análisis de cartera}',
        r'\fancyhead[R]{\small Rentabilidad por periodo}', r'\begin{document}',
        r'{\small\bfseries\color{copper}INFORME DE CARTERA}\par',
        r'{\LARGE\bfseries Rentabilidad por periodo}\par',
        tex_text(short_date(m['start_date']) + ' - ' + short_date(m['end_date'])) + r'\hfill EUR\par',
        r'\AtlasNote{' + ('Contexto vigente en la consulta de exportación.' if current else
            'Informe histórico: el contexto de la cartera ha cambiado.') +
        r' Se exportan exclusivamente los resultados guardados. El detalle de posiciones no está incluido en este informe.}',
        r'\AtlasSection{Resumen del periodo}',
        long_table(['Métrica', 'Valor', 'Calidad'], [.40,.25,.23], [
            [tex_text(label), amount(m[key]['value'], rate=rate), tex_text(STATUS[m[key]['status']])]
            for label,key,rate in [('Resultado neto EUR','pnl',False), ('TWR del periodo','twr',True),
                ('MWR anual - XIRR','mwr',True), ('Flujos externos netos EUR','external_net',False),
                ('Costes y retenciones EUR','costs_eur',False)]]),
        'Patrimonio inicial: ' + amount(m['initial_nav']) + ' EUR. ' +
        'Patrimonio final: ' + amount(m['final_nav']) + ' EUR.',
        r'\par Cierre de referencia: ' + short_date(m['start_date']) + '. Cierre final: ' + short_date(m['end_date']) + '.',
        r'Los flujos corresponden a (referencia, final]: el día de referencia ya está en el patrimonio inicial. '
        r'Costes y retenciones ya están en el resultado y no se descuentan otra vez. '
        r'TWR usa flujos al cierre; MWR es anual, días reales/365.',
        r'\AtlasSection{Evolución del patrimonio}']
    ticks = sorted({0, (len(m['curve'])-1)//2, len(m['curve'])-1}) if m['curve'] else []
    plot = [dict(day=(datetime.fromisoformat(p['date'])-datetime.fromisoformat(m['start_date'])).days,
                 nav=p['nav'] if p['nav'] is not None else 'nan') for p in m['curve']]
    if sum(p['nav'] is not None for p in m['curve']) >= 2:
        parts.extend([r'\begin{tikzpicture}\begin{axis}[width=.89\linewidth,height=62mm,axis lines=left,',
            r'axis line style={rulegray},grid=major,grid style={rulegray!50},unbounded coords=jump,',
            r'tick label style={font=\small\sffamily},scaled y ticks=false,',
            r'yticklabel={\pgfmathprintnumber[fixed,precision=0,1000 sep={.},assume math mode=true]{\tick}},',
            'xtick={' + ','.join(str(plot[i]['day']) for i in ticks) + '},',
            'xticklabels={' + ','.join(short_date(m['curve'][i]['date']) for i in ticks) + '}]',
            r'\addplot[color=slate,thick] table[x=day,y=nav,col sep=comma]{nav-plot.csv};',
            r'\end{axis}\end{tikzpicture}\par',
            r'{\footnotesize EUR, días civiles. Eje vertical recortado; los huecos permanecen discontinuos.}'])
    else:
        parts.append('No hay dos valoraciones disponibles para representar una curva.')
    parts.extend([r'\AtlasSection{Calidad y límites}',
        'Disponibilidad histórica completa según el informe D7.' if m['historical_known'] else 'La fuente no acredita toda la disponibilidad histórica.',
        'Sin benchmark: el informe D7 no guarda una referencia comparable. Sin detalle de efectivo, posiciones o movimientos internos; '
        'los flujos externos y costes sí se conservan.'])
    for key,label in [('pnl','Resultado'),('twr','TWR'),('mwr','MWR'),('external_net','Flujos'),('costs_eur','Costes')]:
        if m[key]['reasons']:
            parts.append(context_table([(label, tex_text(' '.join(REASONS.get(r,r) for r in m[key]['reasons'])))]))
    parts.extend([r'\clearpage\AtlasSection{Cortes diarios}',
        long_table(['Cierre','NAV EUR','Flujo EUR','Factor TWR','Calidad'], [.17,.18,.17,.18,.17],
            [[short_date(p['date']),amount(p['nav']),amount(p['flow_eur']),
              'Sin base' if p['twr_factor'] is None else tex_text(number(p['twr_factor'],6)),
              tex_text(STATUS[p['status']])] for p in m['curve']]),
        r'\AtlasSection{Tramos TWR}',
        long_table(['Inicio','Fin','TWR','Calidad'], [.21,.21,.21,.23],
            [[short_date(s['start_date']),short_date(s['end_date']),amount(s['value'],rate=True),
              tex_text(STATUS[s['status']])] for s in m['twr']['segments']]),
        r'\AtlasSection{Flujos externos}',
        long_table(['Fecha','Moneda','Importe nativo','EUR','Calidad'], [.17,.12,.22,.17,.18],
            [[short_date(f['date']),tex_text(f['currency']),amount(f['native_amount']),amount(f['eur_amount']),
              tex_text(STATUS[f['status']])] for f in m['flows']]) if m['flows'] else 'Sin flujos externos en el periodo.',
        r'\AtlasSection{Costes y retenciones}',
        long_table(['Fecha','Concepto','Nativo','Moneda','EUR'], [.17,.19,.19,.12,.20],
            [[short_date(c['date']),tex_text({'fee':'Comisión','tax':'Retención','charge':'Cargo'}[c['kind']]),
              amount(c['native_amount']),tex_text(c['currency']),amount(c['eur_amount'])] for c in m['costs']])
            if m['costs'] else 'Sin costes registrados en el periodo.',
        r'\AtlasSection{Procedencia y reproducción}',
        context_table([('Cartera',identifier(m['portfolio_id'])), ('Informe D7',identifier(m['source_id'])),
            ('Revisión del libro',tex_text(m['portfolio_revision'])), ('Política',identifier(m['source_policy'])),
            ('Contexto económico',identifier(m['context_hash'])), ('Contenido económico',identifier(m['economic_hash'])),
            ('Informe fuente',identifier(m['source_hash'])), ('Generado UTC',tex_text(generated_at)),
            ('ATLAS / plantilla',tex_text(__version__) + ' / ' + identifier(TEMPLATE))]),
        r'{\footnotesize JSON/CSV conservan cifras y contexto completos. Redondeo solo de presentación. '
        r'SHA-256 verifica integridad, no autenticidad ni recálculo sin las fuentes originales.}',
        r'\end{document}'])
    return '\n'.join(parts).encode('utf-8'), table(plot, ['day','nav'])


def make_files(source, *, current, generated_at=None):
    model = adapt(source)
    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec='seconds')
    parsed = datetime.fromisoformat(timestamp)
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0 or type(current) is not bool:
        raise ValueError('Fecha UTC y vigencia explícita requeridas.')
    rendered, plot = render(model, timestamp, current)
    files = {'source-report.json':encoded(source), 'period-report.json':encoded(model.model_dump(mode='json')),
        'report.tex':rendered, 'atlas-style.tex':STYLE.read_bytes().replace(b'\r\n',b'\n'), 'nav-plot.csv':plot,
        'README.txt': ('ATLAS: informe D7 guardado, formato atlas-period-report-v1.\n'
            'source-report.json conserva el original; la vigencia de consulta está en manifest.json.\n'
            'Detalle de posiciones no guardado: no se completa desde el libro actual.\n'
            'Compilar report.tex con LuaLaTeX/TeX Live 2026, dos pasadas, --nosocket --no-shell-escape.\n'
            'Para compilación gestionada: tools/export_period_latex.py desde ATLAS.\n'
            'Integridad no equivale a autenticidad. No ejecutar fuentes TeX externas o alteradas.\n').encode('utf-8')}
    for filename, values, fields in [('curve.csv',model.curve,list(PerformancePoint.model_fields)),
                                    ('flows.csv',model.flows,list(ExternalFlow.model_fields)),
                                    ('costs.csv',model.costs,list(CostItem.model_fields))]:
        files[filename] = table(rows_csv([v.model_dump(mode='json') for v in values]), fields)
    manifest = dict(format=FORMAT, generated_at=timestamp, current_at_export=current,
        template=TEMPLATE, atlas_version=__version__, economic_hash=model.economic_hash,
        model_hash=digest(model.model_dump(mode='json')), source_hash=digest(source),
        generator_sha256={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            for p in (Path(__file__),Path(__file__).with_name('period_report.py'),Path(__file__).with_name('research_latex.py'))},
        files={n:dict(sha256=hashlib.sha256(v).hexdigest(), bytes=len(v)) for n,v in files.items()})
    files['manifest.json'] = encoded(dict(**manifest, manifest_hash=digest(manifest)))
    if sum(map(len,files.values())) > LIMIT:
        raise ValueError('Informe demasiado grande para exportar (32 MB).')
    return files


def verify_archive(data):
    if len(data) > LIMIT:
        raise ValueError('Paquete demasiado grande.')
    with zipfile.ZipFile(io.BytesIO(data)) as zipped:
        entries = zipped.infolist()
        if len(entries) != len(MEMBERS) or {e.filename for e in entries} != MEMBERS or sum(e.file_size for e in entries) > LIMIT:
            raise ValueError('Contenido de paquete no válido.')
        supplied = {e.filename:zipped.read(e) for e in entries}
    manifest = json.loads(supplied['manifest.json'])
    expected = make_files(json.loads(supplied['source-report.json']), current=manifest['current_at_export'],
                          generated_at=manifest['generated_at'])
    if supplied != expected:
        raise ValueError('Paquete alterado o generador diferente.')
    return manifest

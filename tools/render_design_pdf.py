from pathlib import Path
import re
import html
import json
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, CondPageBreak, LongTable, TableStyle, Flowable
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'docs' / 'atlas_quant_diseno.md'
OUT = ROOT / 'output' / 'pdf' / 'atlas_quant_diseno.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
QA = ROOT / 'tmp' / 'pdfs'
QA.mkdir(parents=True, exist_ok=True)
for name, file in [('Body', 'calibri.ttf'), ('Bold', 'calibrib.ttf'), ('Italic', 'calibrii.ttf'), ('Light', 'calibril.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / file)))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold', italic='Italic', boldItalic='Bold')

NAVY = HexColor('#112C3B')
TEAL = HexColor('#006B6B')
INK = HexColor('#20323D')
MUTED = HexColor('#627480')
PALE = HexColor('#F1F5F6')
W, H = A4
MARGIN = 47
WIDTH = W - MARGIN * 2

body = ParagraphStyle('Body', fontName='Body', fontSize=10.5, leading=14.6, textColor=INK, spaceAfter=8, allowWidows=0, allowOrphans=0)
h2 = ParagraphStyle('Chapter', parent=body, fontName='Bold', fontSize=21, leading=25, textColor=NAVY, spaceBefore=14, spaceAfter=16, keepWithNext=True)
h3 = ParagraphStyle('Subhead', parent=body, fontName='Bold', fontSize=13, leading=17, textColor=TEAL, spaceBefore=12, spaceAfter=7, keepWithNext=True)
cell = ParagraphStyle('Cell', parent=body, fontSize=9, leading=12, spaceAfter=0)
headcell = ParagraphStyle('HeadCell', parent=cell, fontName='Bold', textColor=white)
bullet = ParagraphStyle('Bullet', parent=body, leftIndent=15, bulletIndent=1, spaceAfter=5)
small = ParagraphStyle('Small', parent=body, fontSize=9, leading=12, textColor=MUTED)

def clean(text):
    return text.replace('\u2013', '-').replace('\u2014', '-').replace('\u2011', '-').replace('\u2212', '-')

def inline(text):
    text = clean(text)
    tokens = []
    def save(markup):
        tokens.append(markup)
        return f'ZZTOKEN{len(tokens)-1}ZZ'
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', lambda m: save(f'<link href="{html.escape(m.group(2), quote=True)}" color="#006B6B"><u>{html.escape(m.group(1))}</u></link>'), text)
    text = re.sub(r'`([^`]+)`', lambda m: save(f'<font name="Body" color="#006B6B">{html.escape(m.group(1))}</font>'), text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    for i, token in enumerate(tokens):
        text = text.replace(f'ZZTOKEN{i}ZZ', token)
    return text

class Architecture(Flowable):
    def __init__(self):
        super().__init__()
        self.width = WIDTH
        self.height = 272
    def draw(self):
        c = self.canv
        def box(x, y, w, label, sub=''):
            c.setFillColor(PALE); c.setStrokeColor(HexColor('#B8CFD2'))
            c.roundRect(x, y, w, 46, 5, fill=1, stroke=1)
            c.setFillColor(NAVY); c.setFont('Bold', 10)
            c.drawCentredString(x + w / 2, y + 27, label)
            c.setFillColor(MUTED); c.setFont('Body', 8.5)
            c.drawCentredString(x + w / 2, y + 12, sub)
        def arrow(x1, y1, x2, y2):
            from math import atan2, cos, sin, pi
            c.setStrokeColor(TEAL); c.setFillColor(TEAL); c.setLineWidth(1)
            c.line(x1, y1, x2, y2)
            a = atan2(y2-y1, x2-x1)
            p = c.beginPath(); p.moveTo(x2, y2)
            p.lineTo(x2-5*cos(a-pi/6), y2-5*sin(a-pi/6))
            p.lineTo(x2-5*cos(a+pi/6), y2-5*sin(a+pi/6)); p.close()
            c.drawPath(p, fill=1, stroke=0)
        bw = 154; gap = (WIDTH - 3*bw)/2
        xs = [0, bw+gap, 2*(bw+gap)]
        box(xs[1], 218, bw, 'Interfaz de cartera', 'API local y permisos')
        box(xs[0], 146, bw, 'Datos y calidad', 'Originales y versiones')
        box(xs[1], 146, bw, 'Núcleo financiero', 'Contabilidad, análisis, riesgo')
        box(xs[2], 146, bw, 'Control de órdenes', 'Mandatos, límites, reservas')
        box(xs[0], 68, bw, 'Históricos', 'Parquet y DuckDB')
        box(xs[1], 68, bw, 'Estado duradero', 'SQLite y conciliación')
        box(xs[2], 68, bw, 'Adaptador IBKR', 'TWS o IB Gateway')
        arrow(xs[1]+bw/2,218,xs[1]+bw/2,192)
        arrow(xs[1]+bw,241,xs[2]+bw/2,192)
        arrow(xs[0]+bw,169,xs[1],169)
        arrow(xs[0]+bw/2,146,xs[0]+bw/2,114)
        arrow(xs[1]+bw/2,114,xs[1]+bw/2,146)
        arrow(xs[2]+bw/2,146,xs[2]+bw/2,114)
        arrow(xs[2],91,xs[1]+bw,91)
        c.setFillColor(MUTED); c.setFont('Body',9)
        c.drawString(0, 34, 'La simulación usa el núcleo y sus datos; la ejecución pasa siempre por sus controles.')
        c.drawString(0, 19, 'Diagrama lógico. Un único emisor de órdenes por cuenta.')

class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=54, bottomMargin=44,
            title='ATLAS Quant - Diseño funcional y técnico', author='Diseño preparado para el usuario', subject='Cartera personal, acciones y ETF, análisis y automatización')
        self.addPageTemplates(PageTemplate(id='main', frames=[Frame(MARGIN,44,WIDTH,H-98,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)], onPage=self.decorate))
    def decorate(self,c,d):
        if d.page == 1:
            c.setFillColor(NAVY); c.rect(0,H-23,W,23,fill=1,stroke=0)
        else:
            c.setFont('Bold',8); c.setFillColor(TEAL); c.drawString(MARGIN,H-29,'ATLAS / QUANT')
            c.setFont('Body',8); c.setFillColor(MUTED); c.drawRightString(W-MARGIN,H-29,'DISEÑO FUNCIONAL Y TÉCNICO')
            c.setStrokeColor(HexColor('#D6E1E4')); c.setLineWidth(.6); c.line(MARGIN,H-37,W-MARGIN,H-37)
        c.setFillColor(MUTED); c.setFont('Body',8)
        c.drawString(MARGIN,25,'05.09.2026  |  Especificación v1.0  |  Uso personal')
        c.drawRightString(W-MARGIN,25,str(d.page))
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and f.style.name == 'Chapter':
            title = f.getPlainText()
            key = 'chapter-' + title.split('.')[0]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title,key,0,False)
            self.notify('TOCEntry',(0,title,self.page,key))

story = []
story.append(Spacer(1,57))
story.append(Paragraph('ATLAS',ParagraphStyle('Cover',fontName='Light',fontSize=60,leading=63,textColor=NAVY)))
story.append(Paragraph('QUANT',ParagraphStyle('Cover2',fontName='Bold',fontSize=24,leading=30,textColor=TEAL,spaceAfter=29)))
story.append(Paragraph('Diseño de una plataforma<br/>de cartera personal',ParagraphStyle('Title',fontName='Bold',fontSize=26,leading=32,textColor=NAVY,spaceAfter=20)))
story.append(Paragraph('Acciones y ETF · Análisis y riesgo<br/>Órdenes reales · Automatización por reglas',ParagraphStyle('Deck',parent=body,fontSize=15,leading=21,textColor=MUTED,spaceAfter=34)))
story.append(Paragraph('Una decisión de inversión que puedas reconstruir.',ParagraphStyle('Promise',parent=body,fontSize=14,leading=20,textColor=TEAL,spaceAfter=24)))
story.append(Paragraph('20 secciones · 16 criterios de aceptación · 6 fases de implementación',body))
story.append(Spacer(1,19))
story.append(Paragraph('Preparado a partir del alcance confirmado: cartera personal, acciones y ETF, conexión a bróker y automatización con límites, empezando con recursos gratuitos.',body))
story.append(Spacer(1,14))
story.append(Paragraph('<b>Estado:</b> especificación para implementar. Incluye decisiones, límites, fuentes y pruebas previstas; no acredita software construido ni validación operativa superada.',small))
story.append(PageBreak())
story.append(Paragraph('Contenido',ParagraphStyle('Contents',parent=h2)))
story.append(Paragraph('Las referencias son enlaces activos. Los marcadores del PDF permiten saltar a cada sección.',small))
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle('TOC0',parent=body,fontSize=10.5,leading=15,spaceBefore=5,leftIndent=0,firstLineIndent=0,rightIndent=18)]
story.append(toc)

lines = SRC.read_text(encoding='utf-8').splitlines()
start = next(i for i,l in enumerate(lines) if l.startswith('## 1. '))
lines = lines[start:]
i=0
while i < len(lines):
    line=lines[i].strip()
    if not line:
        i+=1; continue
    if line.startswith('## '):
        story.append(PageBreak() if line.startswith('## 1. ') else CondPageBreak(430)); story.append(Paragraph(inline(line[3:]),h2)); i+=1; continue
    if line.startswith('### '):
        story.append(Paragraph(inline(line[4:]),h3)); i+=1; continue
    if line.startswith('```'):
        i+=1
        while i < len(lines) and not lines[i].strip().startswith('```'): i+=1
        i+=1
        story.append(Architecture()); story.append(Spacer(1,8)); continue
    if line.startswith('|'):
        raw=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            row=[s.strip() for s in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?',s or '') for s in row): raw.append(row)
            i+=1
        n=len(raw[0])
        if n==4: weights=[.20,.28,.29,.23] if raw[0][0]=='Candidato' else [.18,.31,.14,.37]
        elif n==3: weights=[.24,.34,.42]
        else: weights=[.45,.55]
        data=[[Paragraph(inline(s),headcell if idx==0 else cell) for s in row] for idx,row in enumerate(raw)]
        t=LongTable(data,colWidths=[WIDTH*w for w in weights],repeatRows=1,hAlign='LEFT',spaceBefore=4,spaceAfter=12)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
             ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
             ('ROWBACKGROUNDS',(0,1),(-1,-1),[white,PALE]),('LINEBELOW',(0,0),(-1,0),1,TEAL),('LINEBELOW',(0,1),(-1,-1),.3,HexColor('#D6E1E4'))]))
        story.append(t); continue
    match=re.match(r'^(-|\d+\.)\s+(.+)',line)
    if match:
        mark='•' if match.group(1)=='-' else match.group(1)
        story.append(Paragraph(inline(match.group(2)),bullet,bulletText=mark)); i+=1; continue
    block=[line]; i+=1
    while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|- |\d+\. )',lines[i].strip()):
        block.append(lines[i].strip()); i+=1
    story.append(Paragraph(inline(' '.join(block)),body))

Doc(str(OUT)).multiBuild(story)
reader=PdfReader(OUT)
pages=[p.extract_text() or '' for p in reader.pages]
chapters=re.findall(r'^## (\d+\. .+)$',SRC.read_text(encoding='utf-8'),re.M)
joined='\n'.join(pages)
missing=[h for h in chapters if clean(h) not in joined]
links=sum(len(p.get('/Annots',[])) for p in reader.pages)
report={'pages':len(pages),'words_source':len(SRC.read_text(encoding='utf-8').split()),'chapters':len(chapters),'missing_chapters':missing,'annotations':links,'chars_per_page':[len(p) for p in pages],'pdf_bytes':OUT.stat().st_size}
(QA/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
if missing: raise SystemExit('Missing chapters in PDF')

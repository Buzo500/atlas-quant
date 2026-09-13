"""Stateless local research boundary. No catalog, portfolio or holdout writes."""
import hashlib
import json
from typing import Literal

from fastapi import Response
from pydantic import Field

from .computation import bounded_calculation
from .contracts import ResponseModel
from .lab_contracts import LabPeriod
from .retrospective import RetrospectiveRequest, freeze
from .retrospective_package import encoded, run, verify_report, export_bytes, code_hashes
from .simulation_contracts import SimulationConfig
from .strategy_spec import FrozenContract, Hash


class RetrospectiveSettings(RetrospectiveRequest):
    """HTTP arrays; CSV provenance is computed from the received bytes by the server."""
    source_sha256: Literal['server-computed'] = 'server-computed'
    expected_dates: list[str] = Field(min_length=2, max_length=2000)
    early_close_dates: list[str] = Field(default_factory=list, max_length=2000)


class RetrospectivePrepareInput(FrozenContract):
    settings: RetrospectiveSettings
    csv: str = Field(min_length=1, max_length=2_000_000)


class RetrospectiveCalculateInput(FrozenContract):
    frozen_json: str = Field(min_length=50, max_length=3_000_000)
    expected_frozen_hash: Hash


class RetrospectiveReopenInput(FrozenContract):
    report_json: str = Field(min_length=50, max_length=3_000_000)


class RetrospectiveContext(ResponseModel):
    symbol: str
    instrument_id: str
    market: str
    currency: Literal['EUR']
    fast: int
    slow: int
    config: SimulationConfig
    start_date: str
    development_end: str
    development_sessions: int
    holdout_start: str
    holdout_end: str
    holdout_sessions: int
    holdout_evaluated: Literal[False]
    evidence_verified: Literal[False]
    provider: str
    calendar_source: str
    event_review: str
    source_sha256: str
    frozen_hash: str
    warnings: list[str]


class RetrospectivePreview(ResponseModel):
    context: RetrospectiveContext
    frozen_json: str


class RetrospectiveView(ResponseModel):
    context: RetrospectiveContext
    development: LabPeriod
    report_json: str
    report_hash: str
    code_matches: bool


def context(frozen):
    request, reserve = frozen['request'], frozen['holdout']
    return dict(**{k: request[k] for k in ('symbol', 'instrument_id', 'market', 'currency',
        'fast', 'slow', 'config', 'provider', 'calendar_source', 'event_review', 'source_sha256')},
        start_date=frozen['rows'][0]['date'], development_end=frozen['rows'][-1]['date'],
        development_sessions=len(frozen['rows']), holdout_start=reserve['start'], holdout_end=reserve['end'],
        holdout_sessions=reserve['sessions'], holdout_evaluated=False, evidence_verified=False,
        frozen_hash=frozen['frozen_hash'], warnings=frozen['warnings'])


def view(report):
    return dict(context=context(report['frozen']), development=report['result']['development'],
        report_json=encoded(report).decode('utf-8'), report_hash=report['report_hash'],
        code_matches=report['code_sha256'] == code_hashes())


def read_document(text):
    if len(text.encode('utf-8')) > 3_000_000:
        raise ValueError('Documento de investigación demasiado grande.')
    try:
        result = json.loads(text)
    except (ValueError, RecursionError) as exc:
        raise ValueError('Documento JSON inválido.') from exc
    if not isinstance(result, dict):
        raise ValueError('Se requiere un documento de investigación JSON.')
    return result


def register_retrospective_routes(app):
    @app.post('/api/lab/retrospective/prepare', response_model=RetrospectivePreview)
    @bounded_calculation
    def prepare(body: RetrospectivePrepareInput):
        request = RetrospectiveRequest.model_validate_json(encoded(dict(
            **body.settings.model_dump(mode='json', exclude={'source_sha256'}),
            source_sha256=hashlib.sha256(body.csv.encode('utf-8')).hexdigest())))
        frozen = freeze(request, body.csv)
        return dict(context=context(frozen), frozen_json=encoded(frozen).decode('utf-8'))

    @app.post('/api/lab/retrospective/calculate', response_model=RetrospectiveView)
    @bounded_calculation
    def calculate(body: RetrospectiveCalculateInput):
        frozen = read_document(body.frozen_json)
        if frozen.get('frozen_hash') != body.expected_frozen_hash:
            raise ValueError('La selección congelada ha cambiado. Revisa el protocolo de nuevo.')
        try:
            return view(run(frozen))
        except (KeyError, TypeError, AttributeError, RecursionError) as exc:
            raise ValueError('Contenido congelado inválido.') from exc

    @app.post('/api/lab/retrospective/reopen', response_model=RetrospectiveView)
    @bounded_calculation
    def reopen(body: RetrospectiveReopenInput):
        try:
            return view(verify_report(read_document(body.report_json), allow_code_change=True))
        except (KeyError, TypeError, AttributeError, RecursionError) as exc:
            raise ValueError('Contenido del informe inválido.') from exc

    @app.post('/api/lab/retrospective/export', response_class=Response,
        responses={200: {'content': {'application/zip': {'schema': {'type': 'string', 'format': 'binary'}}}}})
    @bounded_calculation
    def export(body: RetrospectiveReopenInput):
        try:
            data = export_bytes(read_document(body.report_json), allow_code_change=True)
        except (KeyError, TypeError, AttributeError, RecursionError) as exc:
            raise ValueError('Contenido del informe inválido.') from exc
        return Response(data, media_type='application/zip', headers={
            'Content-Disposition': 'attachment; filename="atlas-retrospectivo.zip"'})

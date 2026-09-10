from fastapi import Query
from .targets_contracts import (TargetDraftInput, TargetActivateInput, TargetEvaluationInput,
    TargetPreview, TargetHistory, TargetReportPreview, TargetReports, TargetReport)
from .targets_service import TargetsService


def register_targets_routes(app, store):
    service = TargetsService(store)

    @app.post('/api/v2/portfolios/{ident}/targets', response_model=TargetPreview)
    def draft(ident: str, body: TargetDraftInput):
        return service.review(ident, body, 'draft')

    @app.post('/api/v2/portfolios/{ident}/targets/activate', response_model=TargetPreview)
    def activate(ident: str, body: TargetActivateInput):
        return service.review(ident, body, 'activate')

    @app.get('/api/v2/portfolios/{ident}/targets', response_model=TargetHistory)
    def history(ident: str, offset: int = Query(0,ge=0), limit: int = Query(20,ge=1,le=100)):
        return service.history(ident, offset, limit)

    @app.post('/api/v2/portfolios/{ident}/target-reports', response_model=TargetReportPreview)
    def evaluate(ident: str, body: TargetEvaluationInput):
        return service.evaluate(ident, body)

    @app.get('/api/v2/portfolios/{ident}/target-reports', response_model=TargetReports)
    def reports(ident: str, offset: int = Query(0,ge=0), limit: int = Query(20,ge=1,le=100)):
        return service.reports(ident, offset, limit)

    @app.get('/api/v2/portfolios/{ident}/target-reports/{report_id}', response_model=TargetReport)
    def report(ident: str, report_id: str):
        return service.report(ident, report_id)

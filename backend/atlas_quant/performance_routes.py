"""Bounded, explicit period reads and reviewed saved reports; no routine polling."""
from fastapi import Query
from fastapi.responses import Response
from .performance_contracts import PerformanceInput, PerformancePreview, PerformanceReport, PerformanceHistory
from .performance_service import PerformanceService
from .book_contracts import BookErrorResponse


def register_performance_routes(app, store):
    service = PerformanceService(store)

    @app.post('/api/v2/portfolios/{ident}/performance', response_model=PerformancePreview, responses={422:{'model':BookErrorResponse}})
    def calculate(ident: str, body: PerformanceInput):
        return service.calculate(ident, body)

    @app.get('/api/v2/portfolios/{ident}/performance', response_model=PerformanceHistory)
    def history(ident: str, offset: int = Query(0,ge=0), limit: int = Query(20,ge=1,le=100)):
        return service.history(ident,offset,limit)

    @app.get('/api/v2/portfolios/{ident}/performance/{report_id}', response_model=PerformanceReport)
    def read(ident: str, report_id: str):
        return service.read(ident,report_id)

    @app.post('/api/v2/portfolios/{ident}/performance/{report_id}/latex',
              response_class=Response, responses={200:{'content':{'application/zip':{}}}})
    def export_latex(ident: str, report_id: str):
        return Response(service.export_latex(ident, report_id), media_type='application/zip',
            headers={'Cache-Control':'no-store', 'Content-Disposition':'attachment; filename="atlas-cartera-latex.zip"'})

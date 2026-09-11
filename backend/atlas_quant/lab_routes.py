from fastapi import Query
from .lab_contracts import LabInput, LabOpenInput, LabHistory, LabReport, LabReproduction
from .lab_service import LabService


def register_lab_routes(app, store):
    service = LabService(store)

    @app.get('/api/lab/protocols', response_model=LabHistory)
    def history(offset: int = Query(0, ge=0, le=100_000), limit: int = Query(20, ge=1, le=50)):
        return service.history(offset, limit)

    @app.post('/api/lab/protocols', response_model=LabReport)
    def create(body: LabInput):
        return service.create(body)

    @app.get('/api/lab/protocols/{ident}', response_model=LabReport)
    def read(ident: str):
        return service.read(ident)

    @app.post('/api/lab/protocols/{ident}/holdout', response_model=LabReport)
    def open_holdout(ident: str, body: LabOpenInput):
        return service.open_holdout(ident, body)

    @app.post('/api/lab/protocols/{ident}/reproduce', response_model=LabReproduction)
    def reproduce(ident: str):
        return service.reproduce(ident)

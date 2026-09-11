from fastapi import Query
from .lab_contracts import LabInput, LabOpenInput, LabHistory, LabReport, LabReproduction
from .lab_service import LabService
from .candidate_contracts import CandidateInput, CandidateRevisionInput, CandidateRevision, CandidateHistory, CandidateRevisions
from .candidate_service import CandidateService


def register_lab_routes(app, store):
    service = LabService(store)
    candidates = CandidateService(store)

    @app.get('/api/lab/candidates', response_model=CandidateHistory)
    def candidate_history(offset: int = Query(0, ge=0, le=100_000), limit: int = Query(20, ge=1, le=50)):
        return candidates.history(offset, limit)

    @app.post('/api/lab/candidates', response_model=CandidateRevision)
    def candidate_create(body: CandidateInput):
        return candidates.create(body)

    @app.get('/api/lab/candidates/{ident}', response_model=CandidateRevision)
    def candidate_read(ident: str):
        return candidates.read(ident)

    @app.get('/api/lab/candidates/{ident}/revisions', response_model=CandidateRevisions)
    def candidate_revisions(ident: str, offset: int = Query(0, ge=0, le=100), limit: int = Query(20, ge=1, le=50)):
        return candidates.revisions(ident, offset, limit)

    @app.post('/api/lab/candidates/{ident}/revisions', response_model=CandidateRevision)
    def candidate_revise(ident: str, body: CandidateRevisionInput):
        return candidates.revise(ident, body)

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

from fastapi import Query
from .lab_contracts import LabInput, LabOpenInput, LabHistory, LabReport, LabReproduction
from .lab_service import LabService
from .candidate_contracts import CandidateInput, CandidateRevisionInput, CandidateRevision, CandidateHistory, CandidateRevisions
from .candidate_service import CandidateService
from .candidate_contracts import CandidateComparisonInput, CandidateComparison, Status
from .lab_preflight import SourcePreflight, inspect_source
from types import SimpleNamespace
from .robustness_contracts import RobustnessInput, RobustnessReport, RobustnessHistory, RobustnessReproduction
from .robustness_service import RobustnessService


def register_lab_routes(app, store):
    service = LabService(store)
    candidates = CandidateService(store)
    robustness = RobustnessService(store)

    @app.get('/api/lab/robustness', response_model=RobustnessHistory)
    def robustness_history(candidate_id: str = Query(pattern=r'^[0-9a-f]{64}$'),
                           offset: int = Query(0, ge=0, le=100_000), limit: int = Query(20, ge=1, le=20)):
        return robustness.history(candidate_id, offset, limit)

    @app.post('/api/lab/robustness', response_model=RobustnessReport)
    def robustness_create(body: RobustnessInput):
        return robustness.create(body)

    @app.get('/api/lab/robustness/{ident}', response_model=RobustnessReport)
    def robustness_read(ident: str):
        return robustness.read(ident)

    @app.post('/api/lab/robustness/{ident}/reproduce', response_model=RobustnessReproduction)
    def robustness_reproduce(ident: str):
        return robustness.reproduce(ident)

    @app.get('/api/lab/sources/preflight', response_model=SourcePreflight)
    def source_preflight(series_id: str = Query(min_length=1, max_length=100), series_version: int = Query(ge=1)):
        return store.read(lambda w: inspect_source(*service._snapshot(w, SimpleNamespace(series_id=series_id, series_version=series_version))))

    @app.get('/api/lab/candidates/search', response_model=CandidateRevisions)
    def candidate_search(q: str = Query('', max_length=200), status: Status | None = None,
                         offset: int = Query(0, ge=0, le=100_000), limit: int = Query(20, ge=1, le=50)):
        return candidates.search(q.strip(), status or '', offset, limit)

    @app.post('/api/lab/candidates/compare', response_model=CandidateComparison)
    def candidate_compare(body: CandidateComparisonInput):
        return candidates.compare(body)

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

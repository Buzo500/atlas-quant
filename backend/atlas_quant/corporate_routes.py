"""HTTP adapters for the D5 use cases; covered by the app's local write guard."""
from fastapi import Query
from fastapi.responses import PlainTextResponse
from .corporate import EVENT_COLUMNS
from .corporate_service import CorporateService
from .corporate_contracts import (CorporateInput, CorporateRevisionInput, CorporateApplicationInput,
    CorporateCatalog, CorporateEvent, CorporatePreview, CorporatePortfolio, CorporateApplicationPreview,
    CorporateDocuments, CorporateDocument)
from .book_contracts import BookErrorResponse


def register_corporate_routes(app, store):
    service = CorporateService(store)

    @app.get("/api/corporate-events", response_model=CorporateCatalog)
    def catalog(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return service.catalog(offset, limit)

    @app.get("/api/corporate-events/{ident}/versions/{revision}", response_model=CorporateEvent)
    def version(ident: str, revision: int):
        return service.version(ident, revision)

    @app.post("/api/corporate-events/imports", response_model=CorporatePreview, responses={422: {"model": BookErrorResponse}})
    def imports(body: CorporateInput):
        return service.import_events(body)

    @app.post("/api/corporate-events/revisions", response_model=CorporatePreview, responses={422: {"model": BookErrorResponse}})
    def revisions(body: CorporateRevisionInput):
        return service.revise(body)

    @app.get("/api/portfolios/{ident}/corporate-actions", response_model=CorporatePortfolio)
    def read(ident: str, as_of_date: str | None = Query(None, max_length=10),
             revision: int | None = Query(None, ge=1), offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return service.read(ident, as_of_date, revision, offset, limit)

    @app.post("/api/portfolios/{ident}/corporate-actions", response_model=CorporateApplicationPreview, responses={422: {"model": BookErrorResponse}})
    def apply(ident: str, body: CorporateApplicationInput):
        return service.apply(ident, body)

    @app.get("/api/corporate-documents", response_model=CorporateDocuments)
    def global_documents(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return service.documents(offset=offset, limit=limit)

    @app.get("/api/corporate-documents/{document_id}", response_model=CorporateDocument)
    def global_document(document_id: str):
        return service.documents(document_id=document_id)

    @app.get("/api/portfolios/{ident}/corporate-documents", response_model=CorporateDocuments)
    def documents(ident: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return service.documents(ident, offset, limit)

    @app.get("/api/portfolios/{ident}/corporate-documents/{document_id}", response_model=CorporateDocument)
    def document(ident: str, document_id: str):
        return service.documents(ident, document_id=document_id)

    @app.get("/api/templates/corporate-events", response_class=PlainTextResponse)
    def template():
        return PlainTextResponse(",".join(EVENT_COLUMNS)+"\n", media_type="text/csv",
                                 headers={"Content-Disposition": 'attachment; filename="atlas-corporate-events-v1.csv"'})

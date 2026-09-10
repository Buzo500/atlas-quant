"""Versioned D6 HTTP adapters using the existing atomic application services."""
from fastapi import Query
from .book_service import BookService
from .corporate_service import CorporateService
from .book_contracts import ImportInput, ReconciliationInput, CorrectionInput, BookDocuments, BookErrorResponse
from .corporate_contracts import CorporateInput, CorporateRevisionInput, CorporateApplicationInput, CorporateDocuments, CorporateDocument
from .multicurrency_contracts import (NativeBookDetail, NativeBookPreview, NativeReconciliationPreview, NativeBookDocument,
    NativeCorporateCatalog, NativeCorporateEvent, NativeCorporatePreview, NativeCorporatePortfolio, NativeCorporateApplicationPreview)


def register_multicurrency_routes(app, store):
    books = BookService(store, multicurrency=True)
    corporate = CorporateService(store, multicurrency=True)
    errors = {422: {'model': BookErrorResponse}}

    @app.get('/api/v2/portfolios/{ident}/book', response_model=NativeBookDetail)
    def book(ident: str, as_of_date: str | None = Query(None, max_length=10), revision: int | None = Query(None, ge=1), offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return books.read(ident, as_of_date, revision, offset, limit)

    @app.post('/api/v2/portfolios/{ident}/imports', response_model=NativeBookPreview, responses=errors)
    def imports(ident: str, body: ImportInput):
        return books.import_movements(ident, body)

    @app.post('/api/v2/portfolios/{ident}/reconciliations', response_model=NativeReconciliationPreview, responses=errors)
    def reconcile(ident: str, body: ReconciliationInput):
        return books.reconcile(ident, body)

    @app.post('/api/v2/portfolios/{ident}/corrections', response_model=NativeBookPreview, responses=errors)
    def correct(ident: str, body: CorrectionInput):
        return books.correct(ident, body)

    @app.get('/api/v2/portfolios/{ident}/book-documents', response_model=BookDocuments)
    def documents(ident: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return books.documents(ident, offset, limit)

    @app.get('/api/v2/portfolios/{ident}/book-documents/{document_id}', response_model=NativeBookDocument)
    def document(ident: str, document_id: str):
        return books.documents(ident, document_id=document_id)

    @app.get('/api/v2/corporate-events', response_model=NativeCorporateCatalog)
    def catalog(offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return corporate.catalog(offset, limit)

    @app.get('/api/v2/corporate-events/{ident}/versions/{revision}', response_model=NativeCorporateEvent)
    def version(ident: str, revision: int):
        return corporate.version(ident, revision)

    @app.post('/api/v2/corporate-events/imports', response_model=NativeCorporatePreview, responses=errors)
    def events(body: CorporateInput):
        return corporate.import_events(body)

    @app.post('/api/v2/corporate-events/revisions', response_model=NativeCorporatePreview, responses=errors)
    def revise_event(body: CorporateRevisionInput):
        return corporate.revise(body)

    @app.get('/api/v2/portfolios/{ident}/corporate-actions', response_model=NativeCorporatePortfolio)
    def read_actions(ident: str, as_of_date: str | None = Query(None, max_length=10), revision: int | None = Query(None, ge=1), offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return corporate.read(ident, as_of_date, revision, offset, limit)

    @app.post('/api/v2/portfolios/{ident}/corporate-actions', response_model=NativeCorporateApplicationPreview, responses=errors)
    def apply(ident: str, body: CorporateApplicationInput):
        return corporate.apply(ident, body)

    @app.get('/api/v2/portfolios/{ident}/corporate-documents', response_model=CorporateDocuments)
    def application_documents(ident: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return corporate.documents(ident, offset, limit)

    @app.get('/api/v2/portfolios/{ident}/corporate-documents/{document_id}', response_model=CorporateDocument)
    def application_document(ident: str, document_id: str):
        return corporate.documents(ident, document_id=document_id)

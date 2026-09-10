from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .ai import provider_status
from .backtest import run_research
from .contracts import (HealthResponse, StateResponse, DatasetResponse, PortfolioResponse,
                        DatasetPricesResponse, LedgerResponse, ResearchResponse, ExperimentResponse, SettingsResponse)
from .data import parse_prices_csv, price_csv_template, ledger_csv_template
from .datasets import LedgerPreviewConflict
from .prices import PricesNotFound
from .service import Service
from .store import Store, now
from .quality import EvidenceRequest, RevisionRequest, check_research, EXPLORATORY_WARNING
from .quality_service import QualityService
from .quality_contracts import QualityReport, EvidencePreview, RevisionPreview
from .book import BookError, MOVEMENT_COLUMNS, STATEMENT_COLUMNS
from .book_service import BookService
from .corporate_routes import register_corporate_routes
from .multicurrency_routes import register_multicurrency_routes
from .book_contracts import (ImportInput, ReconciliationInput, CorrectionInput, BookDetail,
                            BookPreview, ReconciliationPreview, BookDocuments, BookDocument, BookErrorResponse)
from .worker_lock import WorkerLock
from .catalog import CatalogService, InstrumentInput, ListingInput, AliasInput, IdentityNotFound, RevisionConflict
from .portfolios import PortfolioService
from .identity_contracts import (CatalogResponse, ListingResponse, PortfolioRecord, PortfolioDetail,
                                 BindingPreview, PriceBinding, PortfolioLedgerResponse)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid",allow_inf_nan=False)


class PricesInput(StrictModel):
    csv: str = Field(min_length=1,max_length=8_000_000)
    name: str = Field(min_length=1,max_length=100)
    source: str = Field(min_length=3,max_length=500)
    source_kind: Literal["observed","synthetic"] = "observed"
    dataset_id: str | None = None


class LedgerInput(StrictModel):
    csv: str = Field(min_length=1,max_length=2_000_000)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class PortfolioInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    accounting_policy: Literal["legacy-eur-v1", "atlas-accounting-v2"] = "legacy-eur-v1"


class BindingsInput(StrictModel):
    bindings: list[PriceBinding] = Field(max_length=100)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class Costs(StrictModel):
    initial_cash: float = Field(default=10000,ge=100,le=10_000_000)
    commission_bps: float = Field(default=5,ge=0,le=1000)
    slippage_bps: float = Field(default=5,ge=0,le=1000)
    minimum_fee: float = Field(default=1.25,ge=0,le=1000)
    max_position_weight: float = Field(default=0.25,gt=0,le=1)


class Policy(StrictModel):
    min_oos_observations: int = Field(default=126,ge=60,le=2520)
    min_trades: int = Field(default=10,ge=2,le=1000)
    min_sharpe: float = Field(default=0.5,ge=0,le=10)
    max_drawdown: float = Field(default=0.15,gt=0,le=0.5)
    min_excess_return: float = Field(default=0,ge=0,le=1)
    min_forward_sessions: int = Field(default=20,ge=20,le=504)


class ExperimentInput(StrictModel):
    dataset_id: str
    symbol: str = Field(min_length=1,max_length=50)
    prompt: str = Field(default="Compara mantener el activo con filtros de tendencia y evalúa su robustez neta de costes.",min_length=10,max_length=4000)
    provider: Literal["none","openai","anthropic"] = "none"
    model: str | None = None
    budget_usd: float = Field(default=0,ge=0,le=25)
    hours: float = Field(default=48,ge=1,le=8760)
    auto_paper: bool = False
    costs: Costs = Field(default_factory=Costs)
    policy: Policy = Field(default_factory=Policy)


class ResearchInput(StrictModel):
    dataset_id: str
    symbol: str
    costs: Costs = Field(default_factory=Costs)


class SettingsInput(StrictModel):
    """Partial update: omitted fields retain their current stored value.

    Defaults describe initial settings only; the route excludes every unset field.
    Explicit null values and fields outside this model are rejected.
    """
    kill_switch: bool = Field(default=True, strict=True,
                             description="Cambia solo la parada; si se omite, conserva el valor vigente.")
    max_position_weight: float = Field(default=0.25,gt=0,le=1,
                                       description="Cambia solo el límite; si se omite, conserva el valor vigente.")


class ControlInput(StrictModel):
    action: Literal["pause","resume","cancel"]


class FeedInput(StrictModel):
    symbol: str = Field(min_length=1,max_length=25)
    start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    end: str | None = Field(default=None,pattern=r"^\d{4}-\d{2}-\d{2}$")


def create_app(data_dir=None, run_worker=True):
    data_dir = Path(data_dir or os.environ.get("ATLAS_DATA_DIR",Path(__file__).resolve().parents[2]/"var"/"atlas"))
    store = Store(data_dir/"atlas.sqlite3")
    service = Service(store)
    catalog = CatalogService(store)
    portfolios = PortfolioService(store)
    quality = QualityService(store)
    books = BookService(store)


    @asynccontextmanager
    async def lifespan(app):
        # Recovery must never interrupt a different live executor of this database.
        with WorkerLock(str(store.path) + ".worker.lock"):
            with WorkerLock(str(store.path) + ".tick.lock"):
                store.recover()
            worker = asyncio.create_task(service.worker()) if run_worker else None
            app.state.worker = worker
            try:
                yield
            finally:
                if worker:
                    worker.cancel()
                    with suppress(asyncio.CancelledError):
                        await worker

    app = FastAPI(title="ATLAS Quant",version=__version__,lifespan=lifespan)
    register_corporate_routes(app, store)
    register_multicurrency_routes(app, store)
    app.state.service = service
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=["localhost","127.0.0.1","testserver"])

    @app.middleware("http")
    async def local_guard(request: Request, call_next):
        # Host protection + same-origin/custom header: block drive-by websites against localhost.
        origin = request.headers.get("origin")
        allowed = {"http://localhost:3000","http://127.0.0.1:3000","http://localhost:8000","http://127.0.0.1:8000"}
        if origin and origin not in allowed:
            return JSONResponse({"detail":"Origen no autorizado."},status_code=403)
        if request.method not in ("GET","HEAD","OPTIONS") and request.headers.get("x-atlas-client")!="local-v1":
            return JSONResponse({"detail":"Falta cabecera de cliente local."},status_code=403)
        try:
            length = int(request.headers.get("content-length","0"))
        except ValueError:
            return JSONResponse({"detail":"Content-Length inválido."},status_code=400)
        if length>9_000_000:
            return JSONResponse({"detail":"Carga demasiado grande."},status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(BookError)
    async def book_error(request, exc):
        return JSONResponse({"detail": exc.detail()}, status_code=422)

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail":str(exc)},status_code=422)

    @app.exception_handler(LedgerPreviewConflict)
    async def stale_ledger_preview(request, exc):
        return JSONResponse({"detail":str(exc)},status_code=409)

    @app.exception_handler(RevisionConflict)
    async def stale_identity(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(IdentityNotFound)
    async def missing_identity(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.get("/api/catalog", response_model=CatalogResponse, response_model_exclude_unset=True)
    def read_catalog(revision: int | None = Query(default=None, ge=1)):
        return catalog.read(revision)

    @app.post("/api/catalog/instruments", response_model=CatalogResponse, response_model_exclude_unset=True)
    def add_instrument(body: InstrumentInput):
        return catalog.add("instrument", body.model_dump())

    @app.post("/api/catalog/listings", response_model=CatalogResponse, response_model_exclude_unset=True)
    def add_listing(body: ListingInput):
        return catalog.add("listing", body.model_dump())

    @app.post("/api/catalog/aliases", response_model=CatalogResponse, response_model_exclude_unset=True)
    def add_alias(body: AliasInput):
        return catalog.add("alias", body.model_dump())

    @app.get("/api/catalog/resolve", response_model=ListingResponse, response_model_exclude_unset=True)
    def resolve_alias(provider: str = Query(min_length=1, max_length=100),
                      symbol: str = Query(min_length=1, max_length=50),
                      date: str = Query(min_length=10, max_length=10),
                      market: str | None = Query(default=None, max_length=50),
                      revision: int | None = Query(default=None, ge=1)):
        return catalog.resolve(provider, symbol, date, market, revision)

    @app.get("/api/portfolios", response_model=list[PortfolioRecord])
    def list_portfolios():
        return portfolios.list()

    @app.post("/api/portfolios", response_model=PortfolioRecord, status_code=201)
    def new_portfolio(body: PortfolioInput):
        return portfolios.create(body.name, body.accounting_policy)

    @app.get("/api/portfolios/{ident}", response_model=PortfolioDetail)
    def read_portfolio(ident: str, revision: int | None = Query(default=None, ge=1)):
        return portfolios.read(ident, revision)

    @app.post("/api/portfolios/{ident}/bindings", response_model=BindingPreview)
    def bind_portfolio(ident: str, body: BindingsInput):
        return portfolios.bind(ident, [binding.model_dump() for binding in body.bindings],
                               body.commit, body.preview_token)

    @app.post("/api/portfolios/{ident}/ledger", response_model=PortfolioLedgerResponse)
    def portfolio_ledger(ident: str, body: LedgerInput):
        return portfolios.import_ledger(ident, body.csv, body.commit, body.preview_token)

    @app.get("/api/portfolios/{ident}/book", response_model=BookDetail)
    def read_book(ident: str, as_of_date: str | None = Query(default=None, max_length=10),
                  revision: int | None = Query(default=None, ge=1),
                  offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
        return books.read(ident, as_of_date, revision, offset, limit)

    @app.post("/api/portfolios/{ident}/imports", response_model=BookPreview, responses={422: {"model": BookErrorResponse}})
    def import_book(ident: str, body: ImportInput):
        return books.import_movements(ident, body)

    @app.post("/api/portfolios/{ident}/reconciliations", response_model=ReconciliationPreview, responses={422: {"model": BookErrorResponse}})
    def reconcile_book(ident: str, body: ReconciliationInput):
        return books.reconcile(ident, body)

    @app.post("/api/portfolios/{ident}/corrections", response_model=BookPreview, responses={422: {"model": BookErrorResponse}})
    def correct_book(ident: str, body: CorrectionInput):
        return books.correct(ident, body)

    @app.get("/api/portfolios/{ident}/book-documents", response_model=BookDocuments)
    def book_documents(ident: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
        return books.documents(ident, offset, limit)

    @app.get("/api/portfolios/{ident}/book-documents/{document_id}", response_model=BookDocument)
    def book_document(ident: str, document_id: str):
        return books.documents(ident, document_id=document_id)

    @app.get("/api/templates/book-movements", response_class=PlainTextResponse)
    def book_movement_template():
        return PlainTextResponse(",".join(MOVEMENT_COLUMNS) + "\n", media_type="text/csv",
                                 headers={"Content-Disposition": 'attachment; filename="atlas-movements-v2.csv"'})

    @app.get("/api/templates/book-statement", response_class=PlainTextResponse)
    def book_statement_template():
        return PlainTextResponse(",".join(STATEMENT_COLUMNS) + "\n", media_type="text/csv",
                                 headers={"Content-Disposition": 'attachment; filename="atlas-statement-v2.csv"'})

    @app.get("/api/datasets/{ident}/quality", response_model=QualityReport)
    def read_quality(ident: str, version: int = Query(ge=1), symbol: str = Query(min_length=1, max_length=40),
                     start: str | None = Query(default=None, max_length=10),
                     end: str | None = Query(default=None, max_length=10),
                     offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=500)):
        return quality.read(ident, version, symbol, start=start, end=end, offset=offset, limit=limit)

    @app.post("/api/datasets/{ident}/quality", response_model=EvidencePreview)
    def update_quality(ident: str, body: EvidenceRequest):
        return quality.evidence(ident, body)

    @app.post("/api/datasets/{ident}/revisions", response_model=RevisionPreview)
    def revise_prices(ident: str, body: RevisionRequest):
        return quality.revise(ident, body)

    @app.get("/api/health", response_model=HealthResponse, response_model_exclude_unset=True)
    def health():
        worker = getattr(app.state,"worker",None)
        healthy = not run_worker or (worker is not None and not worker.done())
        return {"status":"ok" if healthy else "worker_failed","version":__version__,"mode":"local","live_available":False,"worker_interval_seconds":30}

    @app.get("/api/state", response_model=StateResponse, response_model_exclude_unset=True)
    def state():
        datasets = [{k:v for k,v in d.items() if k not in ("bars", "quality_evidence", "price_revision")} for d in store.list("dataset")]
        experiments = [{k:v for k,v in j.items() if k not in ("research","forward_result","plan")}
                       for j in store.list("experiment")]
        for job in experiments:
            if job.get("paper_account"):
                job["paper_account"] = {k:v for k,v in job["paper_account"].items() if k!="observed_bars"}
        return {"datasets":datasets,"experiments":experiments,"settings":service.settings(),
                "portfolios": [{k: p[k] for k in ("id", "name", "revision")} for p in portfolios.list()],
                "providers":provider_status(),"audit":store.audit_list(40),"server_time":now()}

    @app.post("/api/datasets/demo", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def demo():
        dataset = service.load_demo()
        return {k:v for k,v in dataset.items() if k not in ("bars", "quality_evidence", "price_revision")}

    @app.post("/api/datasets", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def import_prices(body: PricesInput):
        bars = parse_prices_csv(body.csv)
        if len(bars)>100_000:
            raise ValueError("Máximo 100.000 barras por conjunto.")
        result = service.save_dataset(bars,body.name,body.source_kind,body.source,body.dataset_id)
        return {k:v for k,v in result.items() if k not in ("bars", "quality_evidence", "price_revision")}

    @app.post("/api/feeds", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def feed_connect(body: FeedInput):
        async with service.feed_lock:
            result = await service.connect_feed(body.symbol,body.start,body.end)
        return {k:v for k,v in result.items() if k not in ("bars", "quality_evidence", "price_revision")}

    @app.post("/api/feeds/{ident}/refresh", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def feed_refresh(ident: str):
        result = await service.datasets.refresh_feed(ident, min_interval_seconds=60)
        return {k:v for k,v in result.items() if k not in ("bars", "quality_evidence", "price_revision")}

    @app.get("/api/datasets/{ident}/portfolio", response_model=PortfolioResponse, response_model_exclude_unset=True)
    def portfolio(ident: str):
        return service.portfolio(ident)

    @app.get("/api/datasets/{ident}/prices", response_model=DatasetPricesResponse)
    def prices(ident: str, version: int = Query(ge=1, le=2_147_483_647),
               symbol: str = Query(min_length=1, max_length=50),
               start: str | None = Query(default=None, max_length=10),
               end: str | None = Query(default=None, max_length=10)):
        try:
            return service.datasets.prices(ident, version, symbol, start, end)
        except PricesNotFound as exc:
            raise HTTPException(404, str(exc)) from exc

    @app.post("/api/datasets/{ident}/ledger", response_model=LedgerResponse, response_model_exclude_unset=True)
    async def ledger(ident: str, body: LedgerInput):
        return service.import_ledger(ident, body.csv, body.commit,
                                     preview_token=body.preview_token, require_preview=True)

    @app.get("/api/templates/{kind}",response_class=PlainTextResponse)
    def template(kind: str):
        if kind not in ("prices","ledger"):
            raise HTTPException(404)
        return PlainTextResponse(price_csv_template() if kind=="prices" else ledger_csv_template(),
            media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="atlas-{kind}.csv"'})

    @app.post("/api/research", response_model=ResearchResponse, response_model_exclude_unset=True)
    async def research(body: ResearchInput):
        dataset = service.dataset(body.dataset_id)
        quality_result = check_research(dataset, body.symbol)
        costs = body.costs.model_dump()
        execution_id = uuid4().hex
        candidates = [{"kind":"buy_hold","symbol":body.symbol},
                      {"kind":"sma_cross","symbol":body.symbol,"fast_window":20,"slow_window":100},
                      {"kind":"sma_cross","symbol":body.symbol,"fast_window":50,"slow_window":200}]
        async with service.research_lock:
            started_at = now()
            result = await asyncio.to_thread(run_research,dataset["bars"],candidates,**costs)
        if quality_result["capabilities"]["historical"] != "allowed":
            result["warnings"].append(EXPLORATORY_WARNING)
        execution = {"id": execution_id, "dataset_id": dataset["id"], "dataset_name": dataset["name"],
                     "dataset_version": dataset["version"], "dataset_manifest_hash": dataset["manifest"]["sha256"],
                     "symbol": result["selected_strategy"]["symbol"], "costs": costs,
                     "started_at": started_at, "completed_at": now(),
                     "period": {"start": result["train_period"]["start"], "end": result["test_period"]["end"],
                                "observations": sum(result[key]["observations"]
                                                    for key in ("train_period", "validation_period", "test_period"))}}
        result = {**result, "execution": execution}
        store.audit("research.manual",body.dataset_id,{"data_hash":result["data_hash"],
                    "strategy":result["selected_strategy"], "execution": execution})
        return result

    @app.post("/api/experiments", response_model=ExperimentResponse, response_model_exclude_unset=True,status_code=201)
    async def create_experiment(body: ExperimentInput):
        return service.create_experiment(body.model_dump())

    @app.get("/api/experiments/{ident}", response_model=ExperimentResponse, response_model_exclude_unset=True)
    def get_experiment(ident: str):
        job = store.get("experiment",ident)
        if not job:
            raise HTTPException(404,"Experimento no encontrado.")
        return job

    @app.post("/api/experiments/{ident}/control", response_model=ExperimentResponse, response_model_exclude_unset=True)
    async def control(ident: str, body: ControlInput):
        get_experiment(ident)
        return service.control(ident, body.action)

    @app.post("/api/settings", response_model=SettingsResponse, response_model_exclude_unset=True)
    async def settings(body: SettingsInput):
        """Apply only supplied settings; changing a limit never implies changing the stop."""
        return service.update_settings(body.model_dump(exclude_unset=True))

    @app.get("/api/experiments/{ident}/report",response_class=PlainTextResponse)
    def report(ident: str):
        job = get_experiment(ident)
        from .store import encode
        return PlainTextResponse(encode(job),media_type="application/json",headers={
            "Content-Disposition":f'attachment; filename="atlas-experiment-{ident}.json"'})

    return app


app = create_app()

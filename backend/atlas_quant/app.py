from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .ai import provider_status
from .backtest import run_research
from .contracts import (HealthResponse, StateResponse, DatasetResponse, PortfolioResponse,
                        LedgerResponse, ResearchResponse, ExperimentResponse, SettingsResponse)
from .data import parse_prices_csv, price_csv_template, ledger_csv_template
from .service import Service
from .store import Store, now
from .worker_lock import WorkerLock


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
    kill_switch: bool
    max_position_weight: float = Field(default=0.25,gt=0,le=1)


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

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({"detail":str(exc)},status_code=422)

    @app.get("/api/health", response_model=HealthResponse, response_model_exclude_unset=True)
    def health():
        worker = getattr(app.state,"worker",None)
        healthy = not run_worker or (worker is not None and not worker.done())
        return {"status":"ok" if healthy else "worker_failed","version":__version__,"mode":"local","live_available":False,"worker_interval_seconds":30}

    @app.get("/api/state", response_model=StateResponse, response_model_exclude_unset=True)
    def state():
        datasets = [{k:v for k,v in d.items() if k!="bars"} for d in store.list("dataset")]
        experiments = [{k:v for k,v in j.items() if k not in ("research","forward_result","plan")}
                       for j in store.list("experiment")]
        for job in experiments:
            if job.get("paper_account"):
                job["paper_account"] = {k:v for k,v in job["paper_account"].items() if k!="observed_bars"}
        return {"datasets":datasets,"experiments":experiments,"settings":service.settings(),
                "providers":provider_status(),"audit":store.audit_list(40),"server_time":now()}

    @app.post("/api/datasets/demo", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def demo():
        dataset = service.load_demo()
        return {k:v for k,v in dataset.items() if k!="bars"}

    @app.post("/api/datasets", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def import_prices(body: PricesInput):
        bars = parse_prices_csv(body.csv)
        if len(bars)>100_000:
            raise ValueError("Máximo 100.000 barras por conjunto.")
        result = service.save_dataset(bars,body.name,body.source_kind,body.source,body.dataset_id)
        return {k:v for k,v in result.items() if k!="bars"}

    @app.post("/api/feeds", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def feed_connect(body: FeedInput):
        async with service.feed_lock:
            result = await service.connect_feed(body.symbol,body.start,body.end)
        return {k:v for k,v in result.items() if k!="bars"}

    @app.post("/api/feeds/{ident}/refresh", response_model=DatasetResponse, response_model_exclude_unset=True)
    async def feed_refresh(ident: str):
        result = await service.datasets.refresh_feed(ident, min_interval_seconds=60)
        return {k:v for k,v in result.items() if k!="bars"}

    @app.get("/api/datasets/{ident}/portfolio", response_model=PortfolioResponse, response_model_exclude_unset=True)
    def portfolio(ident: str):
        return service.portfolio(ident)

    @app.post("/api/datasets/{ident}/ledger", response_model=LedgerResponse, response_model_exclude_unset=True)
    async def ledger(ident: str, body: LedgerInput):
        return service.import_ledger(ident, body.csv, body.commit)

    @app.get("/api/templates/{kind}",response_class=PlainTextResponse)
    def template(kind: str):
        if kind not in ("prices","ledger"):
            raise HTTPException(404)
        return PlainTextResponse(price_csv_template() if kind=="prices" else ledger_csv_template(),
            media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="atlas-{kind}.csv"'})

    @app.post("/api/research", response_model=ResearchResponse, response_model_exclude_unset=True)
    async def research(body: ResearchInput):
        dataset = service.dataset(body.dataset_id)
        candidates = [{"kind":"buy_hold","symbol":body.symbol},
                      {"kind":"sma_cross","symbol":body.symbol,"fast_window":20,"slow_window":100},
                      {"kind":"sma_cross","symbol":body.symbol,"fast_window":50,"slow_window":200}]
        async with service.research_lock:
            result = await asyncio.to_thread(run_research,dataset["bars"],candidates,**body.costs.model_dump())
        store.audit("research.manual",body.dataset_id,{"data_hash":result["data_hash"],"strategy":result["selected_strategy"]})
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
        return service.update_settings(body.model_dump())

    @app.get("/api/experiments/{ident}/report",response_class=PlainTextResponse)
    def report(ident: str):
        job = get_experiment(ident)
        from .store import encode
        return PlainTextResponse(encode(job),media_type="application/json",headers={
            "Content-Disposition":f'attachment; filename="atlas-experiment-{ident}.json"'})

    return app


app = create_app()

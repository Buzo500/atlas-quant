"""Bounded research worker. Decisions are rules; LLM output is advisory."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

from . import ai
from .analytics import portfolio_snapshot
from .backtest import backtest, run_research
from .data import build_provenance_manifest, demo_dataset
from .gates import DEFAULT_POLICY, evaluate_evidence
from .store import Store, encode, now


class Service:
    def __init__(self, store: Store):
        self.store = store
        self.lock = asyncio.Lock()
        self.wake = asyncio.Event()

    def settings(self):
        return self.store.get("settings", "main", {"id":"main","kill_switch":True,
            "max_position_weight":0.25,"mode":"paper","live_available":False})

    def dataset(self, ident):
        value = self.store.get("dataset", ident)
        if not value:
            raise ValueError("Conjunto de datos no encontrado.")
        return value

    def save_dataset(self, bars, name, source_kind, source, ident=None, extras=None):
        if any(b["date"] > datetime.now(timezone.utc).date().isoformat() for b in bars):
            raise ValueError("No se admiten precios con fechas futuras.")
        old = self.dataset(ident) if ident else None
        if old:
            # No historical revisions while forward observation refers to a frozen cutoff.
            lookup = {(b["date"],b["symbol"]):b for b in bars}
            if any(lookup.get((b["date"],b["symbol"])) != b for b in old["bars"]):
                raise ValueError("La actualización debe conservar todas las barras anteriores sin cambios. Importe las revisiones como un conjunto nuevo.")
            prior_keys = {(b["date"],b["symbol"]) for b in old["bars"]}
            last_dates = {symbol:max(b["date"] for b in old["bars"] if b["symbol"]==symbol) for symbol in {b["symbol"] for b in old["bars"]}}
            if any((b["date"],b["symbol"]) not in prior_keys and b["date"] <= last_dates.get(b["symbol"],"") for b in bars):
                raise ValueError("Solo se pueden añadir barras posteriores al último día de cada activo; no insertar historia pasada.")
            source_kind, source = old["source_kind"], old["source"]
        value = {**(old or {}),**(extras or {}),"name":name,"bars":bars,"source_kind":source_kind,"source":source,
                 "manifest":build_provenance_manifest(bars,name,source_kind,source)}
        if ident:
            value["id"] = ident
        result = self.store.save_dataset(value)
        self.wake.set()
        return result

    async def connect_feed(self, symbol, start, end=None):
        from .feed import fetch_daily
        snapshot = await asyncio.to_thread(fetch_daily,symbol,start,end)
        dataset = self.save_dataset(snapshot["bars"],symbol+" · Yahoo diario","observed",snapshot["source"],
            extras={"corporate_actions":snapshot["corporate_actions"],"source_metadata":snapshot["source_metadata"],
                    "warnings":snapshot["warnings"],"feed":{"symbol":symbol.upper(),"start":start,
                    "last_attempt":now(),"error":None,"interval_hours":6}})
        self.store.audit("feed.connected",dataset["id"])
        return dataset

    async def refresh_feed(self, ident):
        from .feed import fetch_daily
        dataset = self.dataset(ident)
        feed = dataset.get("feed")
        if not feed:
            raise ValueError("Este conjunto no tiene una fuente automática.")
        feed["last_attempt"] = now()
        self.store.put("dataset",dataset)
        try:
            snapshot = await asyncio.to_thread(fetch_daily,feed["symbol"],feed["start"])
            # Historical revisions fail closed in save_dataset; don't splice them silently.
            dataset = self.save_dataset(snapshot["bars"],dataset["name"],"observed",snapshot["source"],ident,
                extras={"corporate_actions":snapshot["corporate_actions"],"source_metadata":snapshot["source_metadata"],
                        "warnings":snapshot["warnings"],"feed":{**feed,"error":None}})
            self.store.audit("feed.refreshed",dataset["id"])
        except Exception as exc:
            dataset["feed"]["error"] = str(exc) if isinstance(exc,ValueError) else "Error al consultar la fuente; se conserva la última versión."
            self.store.put("dataset",dataset,"feed.failed")
        return dataset

    def load_demo(self):
        existing = next((d for d in self.store.list("dataset") if d.get("demo")),None)
        if existing:
            return existing
        demo = demo_dataset()
        dataset = self.save_dataset(demo["bars"],demo["name"],"synthetic",demo["source"])
        dataset["demo"] = True
        self.store.put("dataset",dataset)
        self.store.put("ledger",{"id":dataset["id"],"events":demo["events"]},"ledger.demo_loaded")
        return dataset

    def portfolio(self, ident):
        dataset = self.dataset(ident)
        events = self.store.get("ledger",ident,{"events":[]})["events"]
        if not events:
            return {"nav":0,"cash":0,"net_contributions":0,"pnl":0,"twr":0,"positions":[],"curve":[],"warnings":["Importa movimientos para valorar tu cartera."]}
        return portfolio_snapshot(events,dataset["bars"])

    def create_experiment(self, request):
        dataset = self.dataset(request["dataset_id"])
        if request["symbol"] not in {b["symbol"] for b in dataset["bars"]}:
            raise ValueError("El activo no pertenece al conjunto de datos.")
        if request["provider"] != "none":
            status = next((s for s in ai.provider_status() if s["provider"] == request["provider"]),None)
            if not status or not status["configured"]:
                raise ValueError("Configura la clave del proveedor en el entorno local antes de crear un experimento con IA.")
            if request["budget_usd"] <= 0:
                raise ValueError("Configura un presupuesto de API mayor que cero.")
            allowed_models = [model["id"] for model in status["models"]]
            request["model"] = request.get("model") or allowed_models[0]
            if request["model"] not in allowed_models:
                raise ValueError("Modelo no admitido para ese proveedor.")
        policy = {**DEFAULT_POLICY,**request.pop("policy",{}),"requested_hours":request["hours"]}
        cutoff = max(b["date"] for b in dataset["bars"] if b["symbol"]==request["symbol"])
        job = {**request,"created_at":now(),"status":"queued","phase":"pending",
               "policy":policy,"dataset_version":dataset["version"],"cutoff":cutoff,
               "frozen_hash":hashlib.sha256(encode(dataset["bars"]).encode()).hexdigest(),
               "spent_usd":0.0,"reserved_usd":0.0,"research":None,"summary":None,
               "error":None,"observation":{},"gate":None,"paper_account":None}
        saved = self.store.put("experiment",job,"experiment.created")
        self.wake.set()
        return saved

    async def _call_ai(self, job, fn, **kwargs):
        remaining = max(0,job["budget_usd"]-job["spent_usd"])
        # Durable conservative reservation BEFORE network I/O. Crash never gives free retry.
        job["reserved_usd"] = remaining
        self.store.put("experiment",job,"ai.reserved")
        try:
            result = await fn(provider=job["provider"],model=job["model"],budget_usd=remaining,**kwargs)
            charged = result["usage"]["estimated_cost_usd"]
        except ai.AIError as exc:
            usage = getattr(exc,"usage",None)
            charged = (usage or {}).get("estimated_cost_usd",0) if isinstance(usage,dict) else 0
            if getattr(exc,"may_be_charged",False):
                charged = max(charged,getattr(exc,"reserved_cost_usd",remaining) or remaining)
            job["spent_usd"] += charged
            job["reserved_usd"] = 0
            self.store.put("experiment",job,"ai.failed")
            raise
        job["spent_usd"] += charged
        job["reserved_usd"] = 0
        self.store.put("experiment",job,"ai.completed")
        return result

    async def start_research(self, job):
        job.update(status="running",phase="planning",started_at=now())
        self.store.put("experiment",job,"experiment.started")
        # Read the original version, never allow a later import to change the selected hypothesis.
        with self.store.transaction() as db:
            import json
            dataset = json.loads(db.execute("SELECT body FROM versions WHERE dataset_id=? AND version=?",
                (job["dataset_id"],job["dataset_version"])).fetchone()[0])
        if job["provider"] == "none":
            candidates = [{"kind":"buy_hold","symbol":job["symbol"]},
                          {"kind":"sma_cross","symbol":job["symbol"],"fast_window":20,"slow_window":100},
                          {"kind":"sma_cross","symbol":job["symbol"],"fast_window":50,"slow_window":200}]
            job["plan"] = {"hypothesis":job["prompt"],"candidates":candidates,
                           "risks":["Catálogo fijo sin IA. Tres candidatos consumen evidencia de validación."]}
        else:
            plan = await self._call_ai(job,ai.propose_strategies,prompt=job["prompt"],
                dataset_summary={"symbols":[job["symbol"]],"manifest":dataset["manifest"],
                                 "hours":job["hours"],"costs":job["costs"]})
            job["plan"] = plan["plan"]
            candidates = plan["plan"]["candidates"]
        job["phase"] = "backtesting"
        self.store.put("experiment",job,"research.started")
        research = await asyncio.to_thread(run_research,dataset["bars"],candidates,**job["costs"])
        research["warnings"].extend(dataset.get("warnings",[]))
        job["research"] = research
        job["phase"] = "reporting"
        self.store.put("experiment",job,"research.completed")
        metrics = research["out_of_sample"]["metrics"]
        selected = research["selected_strategy"]
        engine_summary = (f"La regla seleccionada fue {selected['kind']} sobre {selected['symbol']}. "
            f"En {metrics['observations']} sesiones reservadas obtuvo {metrics['total_return']:.2%} neto de costes, "
            f"frente a {metrics['benchmark_return']:.2%} del benchmark con el mismo peso. "
            f"La caída máxima fue {abs(metrics['max_drawdown']):.2%}, con {metrics['trade_count']} ejecuciones. "
            "La regla queda congelada. Estos resultados históricos no autorizan órdenes reales.")
        job["summary"] = {"summary":engine_summary,
            "limitations":research.get("warnings",[]),"recommendation":"continue_observation","provider":"none"}
        if job["provider"] != "none":
            try:
                compact = {k:v for k,v in research.items() if k not in ("full_result",)}
                compact["out_of_sample"] = {"metrics":research["out_of_sample"]["metrics"]}
                job["summary"] = await self._call_ai(job,ai.summarize_research,research=compact)
            except ai.AIError as exc:
                job["summary"]["limitations"].append("No se obtuvo resumen de IA: " + str(exc))
        job.update(status="observing",phase="forward_observation",observation_started_at=now())
        self.store.put("experiment",job,"experiment.observing")
        await self.observe(job)

    async def observe(self, job):
        dataset = self.dataset(job["dataset_id"])
        elapsed = (datetime.now(timezone.utc)-datetime.fromisoformat(job["observation_started_at"])).total_seconds()/3600
        # Only bars dated AFTER experiment start count; old late-uploaded data are not prospective evidence.
        forward_start = max(job["cutoff"],job["observation_started_at"][:10])
        new_dates = sorted({b["date"] for b in dataset["bars"] if b["symbol"]==job["symbol"] and b["date"]>forward_start})
        fresh = (datetime.now(timezone.utc).date()-datetime.fromisoformat(max(b["date"] for b in dataset["bars"] if b["symbol"]==job["symbol"])).date()).days <= 7
        observation = {"elapsed_hours":elapsed,"new_sessions":len(new_dates),
            "source_kind":dataset["source_kind"],"reconciled":not dataset.get("corporate_actions") and not dataset.get("feed",{}).get("error") and fresh,
            "forward_metrics":None,"last_date":new_dates[-1] if new_dates else None}
        if len(new_dates)>=2:
            forward = await asyncio.to_thread(backtest,dataset["bars"],job["research"]["selected_strategy"],
                evaluation_start=new_dates[0],**job["costs"])
            observation["forward_metrics"] = forward["metrics"]
            job["forward_result"] = forward
        job["observation"] = observation
        job["gate"] = evaluate_evidence(job["research"],observation,job["policy"])
        before = job["status"]
        if job["gate"]["passed"]:
            job["status"] = "eligible_paper"
        elif elapsed >= job["hours"]:
            job["status"] = "completed"
            job["phase"] = "finished"
            job["finished_at"] = now()
            job["completion_note"] = "Plazo finalizado. " + ("Criterios no superados; no se activa ejecución." if not job["gate"]["passed"] else "Criterios superados para simulación.")
        settings = self.settings()
        paper_enabled = job["status"] == "eligible_paper" and job["auto_paper"] and not settings["kill_switch"]
        if paper_enabled or job.get("paper_account"):
            from .paper import new_account, advance_paper
            if not job["paper_account"]:
                job["paper_account"] = new_account(initial_cash=job["costs"]["initial_cash"],started_at_date=max(b["date"] for b in dataset["bars"]))
                self.store.audit("paper.activated",job["id"],{"strategy":job["research"]["selected_strategy"]})
            job["paper_account"] = advance_paper(job["paper_account"],dataset["bars"],job["research"]["selected_strategy"],
                enabled=paper_enabled and job["costs"].get("max_position_weight",1)<=settings["max_position_weight"],
                **{k:v for k,v in job["costs"].items() if k!="initial_cash"})
        self.store.put("experiment",job,"experiment."+job["status"] if before!=job["status"] else None)

    async def tick(self):
        async with self.lock:
            for job in self.store.list("experiment"):
                try:
                    if job["status"]=="queued":
                        await self.start_research(job)
                    elif job["status"] in ("observing","eligible_paper"):
                        await self.observe(job)
                except Exception as exc:
                    # ValueError and our AIError are safe messages. No credentials/raw provider output.
                    public = str(exc) if isinstance(exc,(ValueError,ai.AIError)) else "Error interno. Revisa el registro local y los datos; el experimento no se repetirá automáticamente."
                    job.update(status="failed",error=public,finished_at=now())
                    self.store.put("experiment",job,"experiment.failed")

    async def worker(self):
        while True:
            async with self.lock:
                for dataset in self.store.list("dataset"):
                    feed = dataset.get("feed")
                    if feed and (datetime.now(timezone.utc)-datetime.fromisoformat(feed["last_attempt"])).total_seconds()>=6*3600:
                        await self.refresh_feed(dataset["id"])
            await self.tick()
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(),timeout=30)
            except asyncio.TimeoutError:
                pass

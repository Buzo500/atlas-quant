"""Bounded research worker. Decisions are rules; LLM output is advisory."""
from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from threading import Event
from uuid import uuid4

from . import ai
from .controls import ACTIVE_STATUSES, DEFAULT_SETTINGS, WorkStopped, control_experiment, update_settings
from .datasets import DatasetService
from .worker_lock import WorkerLock
from .backtest import backtest, run_research
from .gates import DEFAULT_POLICY, evaluate_evidence
from .store import Store, encode, now


class Service:
    def __init__(self, store: Store):
        self.store = store
        self.wake = asyncio.Event()
        self.research_lock = asyncio.Lock()
        self.feed_lock = asyncio.Lock()
        self._stops = {}
        self.datasets = DatasetService(store, self.wake.set,
            lambda: datetime.now(timezone.utc), lambda: now())

    def settings(self):
        return self.store.get("settings", "main", dict(DEFAULT_SETTINGS))

    def update_settings(self, values):
        result = update_settings(self.store, values)
        self.wake.set()
        return result

    def control(self, ident, action):
        result = control_experiment(self.store, ident, action)
        if action in ("pause", "cancel") and ident in self._stops:
            self._stops[ident].set()
        self.wake.set()
        return result

    def dataset(self, ident):
        return self.datasets.dataset(ident)

    def save_dataset(self, *args, **kwargs):
        return self.datasets.save_dataset(*args, **kwargs)

    async def connect_feed(self, *args, **kwargs):
        return await self.datasets.connect_feed(*args, **kwargs)

    async def refresh_feed(self, ident):
        return await self.datasets.refresh_feed(ident)

    def load_demo(self):
        return self.datasets.load_demo()

    def portfolio(self, ident):
        return self.datasets.portfolio(ident)

    def import_ledger(self, ident, csv, commit=False, *, preview_token=None, require_preview=True):
        return self.datasets.import_ledger(ident, csv, commit, preview_token=preview_token,
                                           require_preview=require_preview)

    @staticmethod
    def _check_current(current, job):
        if (not current or current["status"] not in ACTIVE_STATUSES
                or current.get("execution_token") != job.get("execution_token")):
            raise WorkStopped()

    def _checkpoint(self, job):
        self._check_current(self.store.get("experiment", job["id"]), job)

    def _save_progress(self, job, fields, event):
        # Only work fields are merged. A concurrent control owns status and orders.
        def apply(current):
            if current.get("execution_token") != job.get("execution_token"):
                raise WorkStopped()
            if current["status"] != "cancelled":
                current.update({key: job[key] for key in fields})
            return current
        current = self.store.update("experiment", job["id"], apply, event)
        self._check_current(current, job)
        job.update(current)

    async def _compute(self, job, fn, *args, **kwargs):
        stop = self._stops.get(job["id"], Event())
        def checkpoint():
            if stop.is_set():
                raise WorkStopped()
        task = asyncio.create_task(asyncio.to_thread(fn, *args, checkpoint=checkpoint, **kwargs))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # Cancelling to_thread alone does not stop its thread. Drain it safely.
            stop.set()
            try:
                await task
            except Exception:
                pass
            raise

    def create_experiment(self, request):
        request = dict(request)
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
        def create(tx):
            if sum(j["status"] in ACTIVE_STATUSES | {"paused"} for j in tx.list("experiment")) >= 10:
                raise ValueError("Máximo 10 experimentos activos o pausados.")
            return tx.put("experiment", job, "experiment.created")
        saved = self.store.atomic(create)
        self.wake.set()
        return saved

    async def _call_ai(self, job, fn, **kwargs):
        def reserve(current):
            self._check_current(current, job)
            if current.get("reserved_usd", 0):
                raise ValueError("Existe una reserva de API sin resolver; no se repite la llamada.")
            remaining = max(0, current["budget_usd"] - current["spent_usd"])
            current["reserved_usd"] = remaining
            return current
        current = self.store.update("experiment", job["id"], reserve, "ai.reserved")
        remaining = current["reserved_usd"]
        job.update(current)

        def settle(charged, event):
            def apply(current):
                if current.get("execution_token") != job.get("execution_token"):
                    raise WorkStopped()
                current["spent_usd"] += charged
                current["reserved_usd"] = 0
                return current
            current = self.store.update("experiment", job["id"], apply, event)
            job["spent_usd"], job["reserved_usd"] = current["spent_usd"], current["reserved_usd"]
        try:
            result = await fn(provider=job["provider"], model=job["model"], budget_usd=remaining, **kwargs)
        except ai.AIError as exc:
            usage = getattr(exc, "usage", None)
            charged = usage.get("estimated_cost_usd", 0) if isinstance(usage, dict) else 0
            if getattr(exc, "may_be_charged", False):
                charged = max(charged, getattr(exc, "reserved_cost_usd", remaining) or remaining)
            settle(charged, "ai.failed")
            raise
        # Unknown transport errors/cancellation leave the reservation durable.
        settle(result["usage"]["estimated_cost_usd"], "ai.completed")
        return result

    async def start_research(self, job):
        self._checkpoint(job)
        dataset = self.store.get_dataset_version(job["dataset_id"], job["dataset_version"])
        if dataset is None:
            raise ValueError("No se encuentra la versión congelada del conjunto.")
        if not job.get("plan"):
            if job["provider"] == "none":
                job["plan"] = {"hypothesis": job["prompt"], "candidates": [
                    {"kind": "buy_hold", "symbol": job["symbol"]},
                    {"kind": "sma_cross", "symbol": job["symbol"], "fast_window": 20, "slow_window": 100},
                    {"kind": "sma_cross", "symbol": job["symbol"], "fast_window": 50, "slow_window": 200}],
                    "risks": ["Catálogo fijo sin IA. Tres candidatos consumen evidencia de validación."]}
            else:
                plan = await self._call_ai(job, ai.propose_strategies, prompt=job["prompt"],
                    dataset_summary={"symbols": [job["symbol"]], "manifest": dataset["manifest"],
                                     "hours": job["hours"], "costs": job["costs"]})
                job["plan"] = plan["plan"]
            self._save_progress(job, ("plan",), "research.planned")
        if not job.get("research"):
            job["phase"] = "backtesting"
            self._save_progress(job, ("phase",), "research.started")
            async with self.research_lock:
                self._checkpoint(job)
                research = await self._compute(job, run_research, dataset["bars"], job["plan"]["candidates"], **job["costs"])
            research["warnings"].extend(dataset.get("warnings", []))
            job.update(research=research, phase="reporting")
            self._save_progress(job, ("research", "phase"), "research.completed")
        if not job.get("summary"):
            research = job["research"]
            metrics, selected = research["out_of_sample"]["metrics"], research["selected_strategy"]
            engine_summary = (f"La regla seleccionada fue {selected['kind']} sobre {selected['symbol']}. "
                f"En {metrics['observations']} sesiones reservadas obtuvo {metrics['total_return']:.2%} neto de costes, "
                f"frente a {metrics['benchmark_return']:.2%} del benchmark con el mismo peso. "
                f"La caída máxima fue {abs(metrics['max_drawdown']):.2%}, con {metrics['trade_count']} ejecuciones. "
                "La regla queda congelada. Estos resultados históricos no autorizan órdenes reales.")
            job["summary"] = {"summary": engine_summary, "limitations": list(research.get("warnings", [])),
                              "recommendation": "continue_observation", "provider": "none"}
            if job["provider"] != "none":
                try:
                    compact = {k: v for k, v in research.items() if k != "full_result"}
                    compact["out_of_sample"] = {"metrics": research["out_of_sample"]["metrics"]}
                    job["summary"] = await self._call_ai(job, ai.summarize_research, research=compact)
                except ai.AIError as exc:
                    job["summary"]["limitations"].append("No se obtuvo resumen de IA: " + str(exc))
            self._save_progress(job, ("summary",), "research.reported")
        def observing(current):
            self._check_current(current, job)
            current.update(status="observing", phase="forward_observation", observation_started_at=now())
            return current
        job.update(self.store.update("experiment", job["id"], observing, "experiment.observing"))
        await self.observe(job)

    async def observe(self, job):
        self._checkpoint(job)
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
            forward = await self._compute(job,backtest,dataset["bars"],job["research"]["selected_strategy"],
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
        def commit_observation(tx):
            current = tx.get("experiment", job["id"])
            self._check_current(current, job)
            latest = tx.get("dataset", job["dataset_id"])
            if latest["version"] != dataset["version"] or latest.get("feed") != dataset.get("feed"):
                self.wake.set()
                return  # New data/quality metadata require a fresh evaluation.
            settings = tx.get("settings", "main", DEFAULT_SETTINGS)
            fields = ("status", "phase", "finished_at", "completion_note", "observation", "gate", "forward_result")
            current.update({key: job[key] for key in fields if key in job})
            paper_enabled = current["status"] == "eligible_paper" and current["auto_paper"] and not settings["kill_switch"]
            if paper_enabled or current.get("paper_account"):
                from .paper import new_account, advance_paper
                if not current.get("paper_account"):
                    current["paper_account"] = new_account(initial_cash=current["costs"]["initial_cash"],
                        started_at_date=max(b["date"] for b in dataset["bars"]))
                    tx.audit("paper.activated", job["id"], {"strategy": current["research"]["selected_strategy"]})
                current["paper_account"] = advance_paper(current["paper_account"], dataset["bars"],
                    current["research"]["selected_strategy"], enabled=paper_enabled and
                    current["costs"].get("max_position_weight", 1) <= settings["max_position_weight"],
                    **{k: v for k, v in current["costs"].items() if k != "initial_cash"})
            tx.put("experiment", current, "experiment." + current["status"] if before != current["status"] else None)
        self.store.atomic(commit_observation)

    async def tick(self):
        # Locks all ticks for this local database, including independent Service objects.
        lock = WorkerLock(str(self.store.path) + ".tick.lock")
        if not lock.acquire():
            return
        try:
            for candidate in self.store.list("experiment"):
                token = uuid4().hex
                def claim(current):
                    if current["status"] not in {"queued", "observing", "eligible_paper"} or current.get("execution_active"):
                        return None
                    current.update(execution_token=token, execution_active=True, control_requested=None)
                    if current["status"] == "queued":
                        current.update(status="running", started_at=current.get("started_at") or now(),
                                       phase=current.get("phase") if current.get("plan") else "planning")
                    return current
                job = self.store.update("experiment", candidate["id"], claim)
                if job.get("execution_token") != token:
                    continue
                self._stops[job["id"]] = Event()
                error = None
                interrupted = False
                try:
                    if job["status"] == "running":
                        await self.start_research(job)
                    else:
                        await self.observe(job)
                except WorkStopped:
                    pass
                except asyncio.CancelledError:
                    interrupted = True
                    raise
                except Exception as exc:
                    error = str(exc) if isinstance(exc, (ValueError, ai.AIError)) else "Error interno. Revisa el registro local y los datos; el experimento no se repetirá automáticamente."
                finally:
                    def finish(current):
                        if current.get("execution_token") != token:
                            return None
                        current.update(execution_active=False, control_requested=None)
                        current.pop("execution_token", None)
                        if current["status"] != "cancelled" and (interrupted or current.get("reserved_usd", 0)):
                            current.update(status="interrupted", error="Proceso interrumpido. Se conserva la reserva de API; no se repite la llamada.")
                        elif error and current["status"] != "cancelled":
                            current.update(status="failed", error=error, finished_at=now())
                        return current
                    self.store.update("experiment", job["id"], finish, "experiment.execution_finished")
                    self._stops.pop(job["id"], None)
        finally:
            lock.release()

    async def worker(self):
        while True:
            self.wake.clear()
            for dataset in self.store.list("dataset"):
                feed = dataset.get("feed")
                if feed and (datetime.now(timezone.utc)-datetime.fromisoformat(feed["last_attempt"])).total_seconds() >= 6*3600:
                    await self.refresh_feed(dataset["id"])
            await self.tick()
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=30)
            except asyncio.TimeoutError:
                pass

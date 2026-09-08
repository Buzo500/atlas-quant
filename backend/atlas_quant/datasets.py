"""Dataset and ledger operations with explicit transactional boundaries."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

from .analytics import portfolio_snapshot
from .data import demo_dataset, parse_ledger_csv
from .prices import PricesNotFound, project_prices, validate_price_range
from .store import now


class LedgerPreviewConflict(ValueError):
    """The reviewed import no longer matches its data and ledger snapshot."""


def _ledger_preview_token(dataset, events, csv):
    # This is a consistency precondition, not an authentication credential.
    # Hash the actual bars rather than trusting a separately stored manifest.
    context = {"purpose": "atlas-ledger-preview-v1", "dataset_id": dataset["id"],
               "dataset_version": dataset["version"], "bars": dataset["bars"],
               "ledger": events, "csv": csv}
    encoded = json.dumps(context, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class DatasetService:
    def __init__(self, store, wake=lambda: None, clock=None, timestamp=now):
        self.store = store
        self.wake = wake
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.timestamp = timestamp

    def dataset(self, ident):
        value = self.store.get("dataset", ident)
        if value is None:
            raise ValueError("Conjunto de datos no encontrado.")
        return value

    def prices(self, ident, version, symbol, start=None, end=None):
        validate_price_range(start, end)
        snapshot = self.store.get_dataset_version(ident, version)
        if snapshot is None:
            raise PricesNotFound("Conjunto o versión de datos no encontrado.")
        return project_prices(snapshot, symbol, start, end)

    def _prepare(self, current, incoming):
        value = {**(current or {}), **incoming}
        if current:
            value["source_kind"], value["source"] = current["source_kind"], current["source"]
        return value

    def _validate_dates(self, bars):
        today = self.clock().date().isoformat()
        if any(bar["date"] > today for bar in bars):
            raise ValueError("No se admiten precios con fechas futuras.")

    def save_dataset(self, bars, name, source_kind, source, ident=None, extras=None):
        self._validate_dates(bars)
        value = {**(extras or {}), "name": name, "bars": bars,
                 "source_kind": source_kind, "source": source}
        if ident is not None:
            value["id"] = ident

        def prepare(current, incoming):
            if ident is not None and current is None:
                raise ValueError("Conjunto de datos no encontrado.")
            return self._prepare(current, incoming)

        result = self.store.save_dataset(value, prepare=prepare)
        self.wake()
        return result

    async def connect_feed(self, symbol, start, end=None):
        from .feed import fetch_daily
        snapshot = await asyncio.to_thread(fetch_daily, symbol, start, end)
        self._validate_dates(snapshot["bars"])
        value = {"name": symbol + " · Yahoo diario", "bars": snapshot["bars"],
                 "source_kind": "observed", "source": snapshot["source"],
                 "corporate_actions": snapshot["corporate_actions"],
                 "source_metadata": snapshot["source_metadata"], "warnings": snapshot["warnings"],
                 "feed": {"symbol": symbol.upper(), "start": start,
                          "last_attempt": self.timestamp(), "error": None, "interval_hours": 6}}

        def connect(work):
            if sum(bool(dataset.get("feed")) for dataset in work.list("dataset")) >= 10:
                raise ValueError("Máximo 10 fuentes automáticas.")
            result = work.save_dataset(value, prepare=self._prepare)
            work.audit("feed.connected", result["id"])
            return result

        result = self.store.atomic(connect)
        self.wake()
        return result

    async def refresh_feed(self, ident, *, min_interval_seconds=0):
        from .feed import fetch_daily
        request_id = uuid.uuid4().hex

        def begin(current):
            feed = current.get("feed")
            if not feed:
                raise ValueError("Este conjunto no tiene una fuente automática.")
            if min_interval_seconds and feed.get("last_attempt"):
                elapsed = (self.clock() - datetime.fromisoformat(feed["last_attempt"])).total_seconds()
                if elapsed < min_interval_seconds:
                    raise ValueError("Espera un minuto entre consultas manuales al proveedor.")
            current["feed"] = {**feed, "last_attempt": self.timestamp(), "request_id": request_id}
            return current

        started = self.store.update("dataset", ident, begin)
        feed = started["feed"]
        try:
            snapshot = await asyncio.to_thread(fetch_daily, feed["symbol"], feed["start"])
            self._validate_dates(snapshot["bars"])

            def finish(current, incoming):
                if not current or current.get("feed", {}).get("request_id") != request_id:
                    return None
                incoming.update(name=current["name"], source_kind=current["source_kind"], source=current["source"])
                refreshed_feed = {**current["feed"], "error": None}
                refreshed_feed.pop("request_id", None)
                incoming["feed"] = refreshed_feed
                return self._prepare(current, incoming)

            def commit(work):
                current = work.get("dataset", ident)
                if not current or current.get("feed", {}).get("request_id") != request_id:
                    return current
                result = work.save_dataset({"id": ident, "bars": snapshot["bars"],
                    "corporate_actions": snapshot["corporate_actions"],
                    "source_metadata": snapshot["source_metadata"], "warnings": snapshot["warnings"]},
                    prepare=finish)
                work.audit("feed.refreshed", ident)
                return result

            result = self.store.atomic(commit)
            self.wake()
            return result
        except Exception as exc:
            error = str(exc) if isinstance(exc, ValueError) else "Error al consultar la fuente; se conserva la última versión."

            def fail(current):
                if current.get("feed", {}).get("request_id") != request_id:
                    return None
                current["feed"] = {**current["feed"], "error": error}
                current["feed"].pop("request_id", None)
                return current

            return self.store.update("dataset", ident, fail, "feed.failed")

    def load_demo(self):
        def load(work):
            existing = next((dataset for dataset in work.list("dataset") if dataset.get("demo")), None)
            if existing:
                return existing
            demo = demo_dataset()
            self._validate_dates(demo["bars"])
            dataset = work.save_dataset({"bars": demo["bars"], "name": demo["name"],
                "source_kind": "synthetic", "source": demo["source"], "demo": True}, prepare=self._prepare)
            work.put("ledger", {"id": dataset["id"], "events": demo["events"]}, "ledger.demo_loaded")
            return dataset

        result = self.store.atomic(load)
        self.wake()
        return result

    def portfolio(self, ident):
        def read(work):
            dataset = work.get("dataset", ident)
            if dataset is None:
                raise ValueError("Conjunto de datos no encontrado.")
            events = work.get("ledger", ident, {"events": []})["events"]
            return dataset, events
        dataset, events = self.store.atomic(read)
        if not events:
            return {"nav": 0, "cash": 0, "net_contributions": 0, "pnl": 0, "twr": 0,
                    "positions": [], "curve": [], "warnings": ["Importa movimientos para valorar tu cartera."]}
        return portfolio_snapshot(events, dataset["bars"])

    def import_ledger(self, ident, csv, commit=False, *, preview_token=None, require_preview=True):
        """Review or confirm an import against one atomic snapshot.

        Trusted in-process imports may explicitly disable the preview requirement;
        the HTTP route always requires it for commits.
        """
        if commit and require_preview and not preview_token:
            raise ValueError("Previsualiza los movimientos antes de confirmar la importación.")
        imported = parse_ledger_csv(csv)
        today = self.clock().date().isoformat()
        if any(event["date"] > today for event in imported):
            raise ValueError("No se admiten movimientos con fechas futuras.")

        def import_events(work):
            dataset = work.get("dataset", ident)
            if dataset is None:
                raise ValueError("Conjunto de datos no encontrado.")
            old = work.get("ledger", ident, {"events": []})["events"]
            token = _ledger_preview_token(dataset, old, csv)
            if commit and preview_token is not None and not hmac.compare_digest(preview_token, token):
                raise LedgerPreviewConflict(
                    "La previsualización ha cambiado. Vuelve a previsualizar los movimientos antes de confirmar.")
            indexed = {event["id"]: event for event in old}
            added = 0
            for event in imported:
                if event["id"] in indexed and indexed[event["id"]] != event:
                    raise ValueError("Un ID ya importado tiene contenido diferente.")
                if event["id"] not in indexed:
                    added += 1
                indexed[event["id"]] = event
            events = sorted(indexed.values(), key=lambda event: event["date"])
            snapshot = portfolio_snapshot(events, dataset["bars"])
            if commit:
                work.put("ledger", {"id": ident, "events": events}, "ledger.imported")
            return {"added": added, "duplicates": len(imported) - added, "total": len(events),
                    "committed": commit, "portfolio": snapshot, "preview_token": token}

        return self.store.atomic(import_events)

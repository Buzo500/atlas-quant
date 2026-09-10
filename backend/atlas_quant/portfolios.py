"""Portfolio application boundary: immutable book, explicit frozen price bindings."""
from __future__ import annotations

import hashlib
import hmac
import json
from collections import Counter
from datetime import datetime, timezone

from .analytics import portfolio_snapshot
from .catalog import IdentityNotFound, RevisionConflict
from .data import parse_ledger_csv
from .quality import report as quality_report


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode()).hexdigest()


class PortfolioService:
    def __init__(self, store):
        self.store = store

    def list(self):
        return self.store.atomic(lambda work: work.portfolio_list())

    def create(self, name, accounting_policy="legacy-eur-v1"):
        name = name.strip()
        if not name or len(name) > 100:
            raise ValueError("Nombre de cartera requerido, máximo 100 caracteres.")
        def save(work):
            value = work.create_portfolio(name, accounting_policy=accounting_policy)
            work.audit("portfolio.created", value["id"])
            return value
        return self.store.atomic(save)

    @staticmethod
    def _context(work, ident, revision=None, bindings=None, *, include_entries=True):
        try:
            portfolio = work.portfolio_record(ident, revision)
        except KeyError as exc:
            raise IdentityNotFound(exc.args[0]) from exc
        catalog = work.catalog(portfolio["catalog_revision"]) if revision is not None and portfolio["catalog_revision"] else work.catalog()
        listings = {item["id"]: item for item in catalog["listings"]}
        selected = portfolio["bindings"] if bindings is None else bindings
        seen, series, datasets = set(), set(), {}
        for binding in selected:
            listing_id = binding["listing_id"]
            if listing_id not in listings:
                raise IdentityNotFound("Cotización no encontrada en el catálogo del corte.")
            if listing_id in seen:
                raise ValueError("Una cotización solo puede tener una fuente de precios en este corte.")
            seen.add(listing_id)
            key = (binding["dataset_id"], binding["dataset_version"])
            series_key = (*key, binding["symbol"])
            if series_key in series:
                raise ValueError("Una serie de precios no puede identificar dos cotizaciones en la misma cartera.")
            series.add(series_key)
            if key not in datasets:
                row = work.dataset_version(*key)
                if row is None:
                    raise IdentityNotFound("Versión de precios no encontrada.")
                datasets[key] = row
            bars = [bar for bar in datasets[key]["bars"] if bar["symbol"] == binding["symbol"]]
            if not bars:
                raise ValueError("El símbolo no pertenece a esa versión de precios.")
            if any(bar.get("currency", "EUR") != listings[listing_id]["currency"] for bar in bars):
                raise ValueError("La moneda de los precios no coincide con la cotización.")
            identity = datasets[key].get('listing_id')
            if identity is not None and identity != listing_id:
                raise ValueError('La serie nativa pertenece a otra cotización; no se puede cambiar su identidad mediante un vínculo.')
        return dict(portfolio=portfolio, catalog=catalog, entries=work.portfolio_events(portfolio) if include_entries else [],
                    bindings=selected, datasets=list(datasets.values()))

    @staticmethod
    def _value(context):
        portfolio = context["portfolio"]
        if portfolio["accounting_policy"] == "atlas-accounting-v2":
            return dict(portfolio=portfolio, entries=context["entries"], value=None,
                context=dict(portfolio_id=portfolio["id"], portfolio_revision=portfolio["revision"],
                    catalog_revision=context["catalog"]["revision"], accounting_policy=portfolio["accounting_policy"],
                    bindings=context["bindings"], data_hash=fingerprint(context["datasets"])),
                status="unavailable", quality=[],
                warnings=["Libro v2: efectivo, cantidades y coste disponibles sin precios. Valoración y rentabilidad v2 pendientes de D6/D7."])
        datasets = {(d["id"], d["version"]): d for d in context["datasets"]}
        labels, bars = {}, []
        for binding in context["bindings"]:
            listing_id = binding["listing_id"]
            # The legacy kernel uppercases identifiers. Translate IDs explicitly.
            symbol = listing_id.upper()
            labels[symbol] = binding["symbol"]
            dataset = datasets[(binding["dataset_id"], binding["dataset_version"])]
            bars.extend({**bar, "symbol": symbol} for bar in dataset["bars"] if bar["symbol"] == binding["symbol"])
        events = [{**item["event"], "symbol": item["listing_id"].upper() if item["listing_id"] else None}
                  for item in context["entries"]]
        snapshot = portfolio_snapshot(events, bars)
        # Preserve legacy presentation order; listing IDs remain separately visible.
        for position in snapshot["positions"]:
            position["listing_id"] = position["symbol"].lower()
            position["symbol"] = labels[position["symbol"]]
        snapshot["positions"].sort(key=lambda position: (position["symbol"], position["listing_id"]))
        if not events:
            snapshot["warnings"] = ["Importa movimientos para valorar tu cartera."]
        quality = []
        if snapshot["curve"]:
            cutoff = snapshot["curve"][-1]["date"]
            held = {p["listing_id"] for p in snapshot["positions"]}
            for binding in context["bindings"]:
                if binding["listing_id"] in held:
                    dataset = datasets[(binding["dataset_id"], binding["dataset_version"])]
                    quality.append(quality_report(dataset, binding["symbol"], start=cutoff, end=cutoff, limit=0))
        return dict(portfolio=portfolio, context=dict(portfolio_id=portfolio["id"],
            portfolio_revision=portfolio["revision"], catalog_revision=context["catalog"]["revision"],
            accounting_policy=portfolio["accounting_policy"], bindings=context["bindings"],
            data_hash=fingerprint(context["datasets"])), value=snapshot,
            entries=context["entries"], status="available", warnings=[], quality=quality)

    def read(self, ident, revision=None):
        context = self.store.atomic(lambda work: self._context(work, ident, revision))
        try:
            return self._value(context)
        except ValueError as exc:
            # A readable book does not imply that enough prices exist to value it.
            return dict(portfolio=context["portfolio"], entries=context["entries"], value=None,
                context=dict(portfolio_id=ident, portfolio_revision=context["portfolio"]["revision"],
                    catalog_revision=context["catalog"]["revision"], accounting_policy="legacy-eur-v1",
                    bindings=context["bindings"], data_hash=fingerprint(context["datasets"])),
                status="unavailable", warnings=[str(exc)])

    def bind(self, ident, bindings, commit=False, preview_token=None):
        if len(bindings) > 100:
            raise ValueError("Máximo 100 vínculos por cartera.")
        # Canonical ordering makes the context independent of form row order.
        bindings = sorted(bindings, key=lambda item: item["listing_id"])
        context = self.store.atomic(lambda work: self._context(work, ident, bindings=bindings))
        result = self._value(context)  # No write lock held during valuation.
        token = fingerprint(dict(purpose="atlas-bindings-v1", context=context))
        if commit:
            if not preview_token or not hmac.compare_digest(preview_token, token):
                raise RevisionConflict("El corte ha cambiado. Previsualiza los vínculos de nuevo.")
            def save(work):
                current = self._context(work, ident, bindings=bindings)
                if fingerprint(dict(purpose="atlas-bindings-v1", context=current)) != token:
                    raise RevisionConflict("El corte ha cambiado durante la valoración. Vuelve a previsualizar.")
                portfolio = current["portfolio"]
                if sorted(portfolio["bindings"], key=lambda item: item["listing_id"]) != bindings:
                    work.write_portfolio_revision(ident, portfolio["event_ids"], bindings)
                    work.audit("portfolio.bindings_changed", ident, {"previous_revision": portfolio["revision"]})
                return work.portfolio_record(ident)
            result["portfolio"] = self.store.atomic(save)
            result["context"]["portfolio_revision"] = result["portfolio"]["revision"]
        return {**result, "committed": commit, "preview_token": token}

    def import_ledger(self, ident, csv, commit=False, preview_token=None):
        imported = parse_ledger_csv(csv)
        if len(imported) > 10_000:
            raise ValueError("Máximo 10.000 movimientos por lote.")
        if any(event["date"] > datetime.now(timezone.utc).date().isoformat() for event in imported):
            raise ValueError("No se admiten movimientos con fechas futuras.")
        context = self.store.atomic(lambda work: self._context(work, ident))
        if context["portfolio"]["accounting_policy"] != "legacy-eur-v1":
            raise ValueError("Esta cartera requiere el formulario de movimientos CSV v2.")
        original = fingerprint(context)
        token = fingerprint(dict(purpose="atlas-portfolio-ledger-v1", context=original, csv=csv))
        symbols = {}
        for binding in context["bindings"]:
            symbols.setdefault(binding["symbol"], set()).add(binding["listing_id"])
        entries = list(context["entries"])
        existing = {item["event"]["id"]: item for item in entries}
        sequence = Counter(item["date"] for item in entries)
        added_entries = []
        for event in imported:
            previous = existing.get(event["id"])
            if previous:
                if previous["event"] != event:
                    raise ValueError("Un ID ya importado tiene contenido diferente.")
                continue
            listing_id = None
            if event.get("symbol"):
                matches = symbols.get(event["symbol"], set())
                if len(matches) != 1:
                    raise ValueError("Símbolo sin vínculo o ambiguo. Revisa las cotizaciones de la cartera.")
                listing_id = next(iter(matches))
            sequence[event["date"]] += 1
            item = dict(event=event, listing_id=listing_id, date=event["date"], day_sequence=sequence[event["date"]])
            entries.append(item)
            existing[event["id"]] = item
            added_entries.append(item)
        entries.sort(key=lambda item: (item["date"], item["day_sequence"]))
        snapshot = self._value({**context, "entries": entries})["value"]
        if commit:
            if not preview_token or not hmac.compare_digest(preview_token, token):
                raise RevisionConflict("La previsualización ha cambiado. Revisa los movimientos de nuevo.")
            def save(work):
                current = self._context(work, ident)
                if fingerprint(current) != original:
                    raise RevisionConflict("El corte ha cambiado durante la valoración. Vuelve a previsualizar.")
                added = work.append_entries(current["portfolio"], added_entries)
                if added:
                    work.audit("ledger.imported", ident, {"added": added})
            self.store.atomic(save)
        return dict(added=len(added_entries), duplicates=len(imported)-len(added_entries), total=len(entries),
                    committed=commit, portfolio=snapshot, preview_token=token)

"""D5 use cases: one coherent context and atomic, versioned confirmations."""
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hmac

from .book import BookError, balance, cutoff, parse_movements, resolve_mapping, text_field, decimal_text, bounded, validate_currencies
from .book_service import BookService, payload
from .catalog import IdentityNotFound, RevisionConflict
from .corporate import (parse_events, event_economics, event_for, application, link_movement,
                        validate_dependencies, prepare_applications)
from .portfolios import fingerprint


def now():
    return datetime.now(timezone.utc).isoformat()


class CorporateService:
    def __init__(self, store, *, multicurrency=False):
        self.store = store
        self.multicurrency = multicurrency
        self.books = BookService(store, multicurrency=multicurrency)

    def _parse_events(self, body, catalog):
        mapping = self.books._mapping(body.mapping, catalog)
        parsed = parse_events(body.csv, mapping, body.verified, body.evidence, multicurrency=self.multicurrency)
        validate_currencies(parsed, catalog)
        return parsed

    def _currency(self, event):
        if not self.multicurrency and event['currency'] != 'EUR':
            raise BookError('unsupported_currency', 'El evento USD requiere la API multidivisa /api/v2.')

    @staticmethod
    def _context(work):
        return dict(catalog=work.catalog(), corporate=work.corporate_state())

    def _catalog(self, context, offset=0, limit=100):
        state = context["corporate"]
        all_events = [e for e in state['events'] if self.multicurrency or e['currency'] == 'EUR']
        events = all_events[offset:offset+limit]
        ids = {e["id"] for e in events}
        return dict(revision=state["revision"], catalog_revision=context["catalog"]["revision"],
                    events=events, sources=[s for s in state["sources"] if s["event_id"] in ids],
                    total=len(all_events), offset=offset, limit=limit)

    def catalog(self, offset=0, limit=100):
        return self._catalog(self.store.atomic(self._context), offset, limit)

    def version(self, ident, revision):
        result = self.store.atomic(lambda w: w.corporate_version(ident, revision))
        if result is None:
            raise IdentityNotFound("Revisión del evento no encontrada.")
        self._currency(result)
        return result

    @staticmethod
    def _token(kind, context, body):
        return fingerprint(dict(purpose="atlas-corporate-"+kind, context=context, payload=payload(body)))

    @staticmethod
    def _check_token(token, body):
        if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
            raise RevisionConflict("Previsualización ausente u obsoleta; revisa de nuevo.")

    def _save_catalog(self, context, body, token, document, events, sources):
        self._check_token(token, body)
        def save(work):
            current = self._context(work)
            if fingerprint(current) != fingerprint(context):
                raise RevisionConflict("Catálogo o eventos modificados durante el cálculo; no se ha confirmado.")
            if work.corporate_document(document["id"]):
                return current
            for value in events:
                work.save_corporate_event(value)
            for value in sources:
                work.save_corporate_source(value)
            work.save_corporate_document(document)
            work.audit("corporate."+document["kind"], document["id"], dict(events=[e["id"] for e in events], sources=len(sources)))
            return self._context(work)
        return self.store.atomic(save)

    @staticmethod
    def _document(kind, body, result, ident=None, context=None):
        return dict(id=fingerprint(dict(kind=kind, payload=payload(body), portfolio=ident, context=context)),
            portfolio_id=ident, kind=kind, created_at=now(), evidence=payload(body), result=result)

    def import_events(self, body):
        context = self.store.atomic(self._context)
        if context["corporate"]["revision"] != body.expected_revision:
            raise RevisionConflict("El catálogo de eventos cambió.")
        source = text_field(body.source, "source")
        parsed = self._parse_events(body, context['catalog'])
        events = {e["id"]: e for e in context["corporate"]["events"]}
        sources = {(s["source"], s["external_id"]): s for s in context["corporate"]["sources"]}
        added, aliases, duplicates, seen = [], [], 0, set()
        for line, external, value in parsed:
            seen.add(external)
            key = source, external
            content_hash = fingerprint(value)
            if key in sources:
                old = sources[key]
                if old["content_hash"] != content_hash or body.event_mapping.get(external, old["event_id"]) != old["event_id"]:
                    raise BookError("duplicate_conflict", "ID de fuente con datos distintos; usa la revisión del evento.", line)
                duplicates += 1
                continue
            target = body.event_mapping.get(external)
            if target:
                if target not in events or event_economics(events[target]) != event_economics(value) or events[target]["cancelled"]:
                    raise BookError("corporate_alias_mismatch", "La segunda fuente no describe el mismo evento económico vigente.", line)
            else:
                possible = [e for e in events.values() if e["listing_id"] == value["listing_id"] and e["event_type"] == value["event_type"]
                            and e["effective_date"] == value["effective_date"] and not e["cancelled"]]
                if possible:
                    text_field(body.distinct_reasons.get(external, ""), "distinct_event_reason", line, 500)
                target = fingerprint(["corporate-event", source, external])
                event = {**value, "id": target, "revision": 1, "created_at": now(), "reason": "Importación revisada"}
                events[target] = event
                added.append(event)
            alias = dict(source=source, external_id=external, event_id=target,
                         source_reference=value["source_reference"], content_hash=content_hash)
            aliases.append(alias)
            sources[key] = alias
        if (set(body.event_mapping) | set(body.distinct_reasons)) - seen:
            raise BookError("corporate_mapping_unused", "Mapeo o explicación para un ID ausente del CSV.")
        updated = {**context, "corporate": dict(events=list(events.values()), sources=list(sources.values()),
                    revision=context["corporate"]["revision"]+len(added)+len(aliases))}
        result = self._catalog(updated, body.offset, body.limit)
        token = self._token("import", context, body)
        document = self._document("import", body, dict(added=len(added), duplicates=duplicates))
        if body.commit:
            updated = self._save_catalog(context, body, token, document, added, aliases)
            result = self._catalog(updated, body.offset, body.limit)
        return {**result, "added": len(added), "duplicates": duplicates,
                "committed": body.commit, "preview_token": token, "document_id": document["id"]}

    def revise(self, body):
        context = self.store.atomic(self._context)
        state = context["corporate"]
        if state["revision"] != body.expected_revision:
            raise RevisionConflict("El catálogo de eventos cambió.")
        previous = next((e for e in state["events"] if e["id"] == body.event_id), None)
        if previous is None:
            raise IdentityNotFound("Evento no encontrado.")
        self._currency(previous)
        if previous["revision"] != body.event_revision:
            raise RevisionConflict("La revisión del evento cambió.")
        reason = text_field(body.reason, "reason", limit=500)
        if body.action == "cancel":
            if body.csv or body.mapping or body.verified or body.evidence:
                raise BookError("incompatible_field", "Cancelar el evento solo requiere motivo; no modifica aplicaciones existentes.")
            if previous["cancelled"]:
                raise BookError("corporate_already_cancelled", "El evento ya está cancelado.")
            value = {**previous, "cancelled": True}
        else:
            parsed = self._parse_events(body, context['catalog'])
            if len(parsed) != 1 or parsed[0][2]["listing_id"] != previous["listing_id"] or parsed[0][2]["event_type"] != previous["event_type"]:
                raise BookError("corporate_revision_target", "Una revisión conserva identidad, cotización y tipo; requiere una fila.")
            if not any(s["event_id"] == body.event_id and s["external_id"] == parsed[0][1] for s in state["sources"]):
                raise BookError("corporate_revision_target", "Usa un ID externo ya asociado a este evento.")
            value = {**previous, **parsed[0][2]}
        value.update(revision=previous["revision"]+1, reason=reason, created_at=now())
        updated = {**context, "corporate": {**state, "revision": state["revision"]+1,
                   "events": [value if e["id"] == value["id"] else e for e in state["events"]]}}
        result = self._catalog(updated, body.offset, body.limit)
        token = self._token("revision", context, body)
        document = self._document("revision", body, dict(event=value), context=state["revision"])
        if body.commit:
            updated = self._save_catalog(context, body, token, document, [value], [])
            result = self._catalog(updated, body.offset, body.limit)
        return {**result, "added": 0, "duplicates": 0, "committed": body.commit,
                "preview_token": token, "document_id": document["id"]}

    @staticmethod
    def _portfolio_context(work, ident, revision=None):
        context = BookService._context(work, ident, revision, history=True)
        context.setdefault("applications", [])
        if "corporate" not in context:
            context["corporate"] = work.corporate_state()
        prices = []
        for binding in context["portfolio"]["bindings"]:
            data = work.dataset_version(binding["dataset_id"], binding["dataset_version"])
            current = work.get("dataset", binding["dataset_id"])
            if data:
                prices.append(dict(binding=binding, current_version=current["version"] if current else None,
                    evidence=data.get("quality_evidence", {}).get(binding["symbol"], {}),
                    dates=[b["date"] for b in data["bars"] if b["symbol"] == binding["symbol"]]))
        context["prices"] = prices
        return context

    def _portfolio(self, context, day, offset=0, limit=100):
        current = {e["id"]: e for e in context["corporate"]["events"]}
        entries = context["entries"]
        movements = {e["event"].get("external_key"): e for e in entries}
        applications, linked, pending = [], set(), {'EUR': Decimal(0)}
        for app in context["applications"]:
            if app["effective_date"] > day:
                continue
            event = app["event_snapshot"]
            self._currency(event)
            valid = bool(current.get(app["event_id"], {}).get("revision") == app["event_revision"])
            warnings = []
            if not valid:
                warnings.append("El evento tiene otra revisión: se conserva el efecto confirmado hasta revisar su aplicación.")
            movement = movements.get(app["movement_key"]) if not app["cancelled"] else None
            paid = bool(movement and movement["date"] <= day)
            if movement:
                linked.add(app["movement_key"])
            receivable = Decimal(app["gross_amount"]) if app["event_type"] == "dividend" and not paid and not app["cancelled"] else Decimal(0)
            with localcontext() as ctx:
                ctx.prec = 64
                pending[event['currency']] = pending.get(event['currency'], Decimal(0)) + receivable
                bounded(pending[event['currency']], "pending_receivables")
            status = "cancelled" if app["cancelled"] else "outdated" if not valid else (
                "applied" if app["event_type"] == "split" else "reconciled" if paid else "pending_payment")
            price_status = "not_applicable"
            if app["event_type"] == "split":
                price_status = "not_accredited"
                for price in context["prices"]:
                    binding, evidence = price["binding"], price["evidence"]
                    if (valid and not app["cancelled"] and binding["listing_id"] == event["listing_id"] and price["current_version"] == binding["dataset_version"]
                            and evidence.get("price_basis") == "raw" and evidence.get("basis_verified") is True
                            and any(event["effective_date"] <= d <= day for d in price["dates"])):
                        price_status = "compatible"
                if price_status != "compatible":
                    warnings.append("Split contable separado de valoración: falta una marca posterior con base bruta acreditada y vigente.")
            applications.append({**app, "current": valid, "status": status,
                                 "receivable": decimal_text(receivable, money=True), "price_status": price_status, "warnings": warnings})
        unlinked = [e["event"]["id"] for e in entries if e["event"]["kind"] == "dividend_payment"
                    and e["date"] <= day and e["event"]["external_key"] not in linked]
        warnings = ["Cobros sin derecho histórico acreditado: el tramo exfecha–pago no permite rentabilidad completa."] if unlinked else []
        if any(not a["current"] and not a["cancelled"] for a in applications):
            warnings.append("Hay aplicaciones desactualizadas que requieren revisión.")
        result = dict(portfolio_id=context["portfolio"]["id"], portfolio_revision=context["portfolio"]["revision"],
            corporate_revision=context["corporate"]["revision"], as_of_date=day,
            applications=applications[offset:offset+limit], total=len(applications), offset=offset, limit=limit,
            balance=self.books._balance(entries, day, context["portfolio"]["accounting_policy"]),
            unlinked_payments=unlinked, warnings=warnings)
        if self.multicurrency:
            result['pending_receivables_by_currency'] = [dict(currency=c, amount=decimal_text(v, money=True)) for c, v in sorted(pending.items())]
        else:
            result['pending_receivables'] = decimal_text(pending['EUR'], money=True)
        return result

    def read(self, ident, day=None, revision=None, offset=0, limit=100):
        day = cutoff(day or datetime.now(timezone.utc).date().isoformat())
        context = self.store.atomic(lambda w: self._portfolio_context(w, ident, revision))
        return self._portfolio(context, day, offset, limit)

    def apply(self, ident, body):
        context = self.store.atomic(lambda w: self._portfolio_context(w, ident))
        BookService._revision(context, body.expected_revision)
        BookService._native(context)
        BookService._source(context, body.source, body.source_account)
        apps = {a["event_id"]: a for a in context["applications"]}
        previous = apps.get(body.event_id)
        if previous:
            self._currency(previous['event_snapshot'])
        entries, added = list(context["entries"]), []
        day = datetime.now(timezone.utc).date().isoformat()
        if body.action == "cancel":
            text_field(body.reason, "reason", limit=500)
            if body.review or body.movement_id or body.csv or not previous or previous["cancelled"]:
                raise BookError("corporate_cancel_target", "Cancelar requiere una aplicación efectiva y motivo, sin otros campos.")
            if (previous["source"], previous["source_account"]) != (body.source, body.source_account):
                raise BookError("account_mismatch", "La cancelación debe conservar fuente y cuenta.")
            if previous["movement_key"]:
                raise BookError("corporate_linked_movement", "Primero revisa la anulación del movimiento vinculado en el libro; no se elimina su efecto en silencio.")
            updated = {**previous, "revision": previous["revision"]+1, "cancelled": True}
        else:
            if not body.review:
                raise BookError("corporate_review_required", "Revisión de evidencia y secuencia requerida.")
            event = event_for(context["corporate"], body.event_id, body.review.event_revision)
            self._currency(event)
            if body.csv and body.movement_id:
                raise BookError("corporate_duplicate", "Elige crear un movimiento o enlazar uno existente, nunca ambos.")
            if body.csv:
                parsed = parse_movements(body.csv, {"ASSET": event["listing_id"]}, day, {},
                    corporate={"EVENT": event}, reviews={event["id"]: body.review.model_dump()}, multicurrency=self.multicurrency)
                validate_currencies(parsed, context['catalog'])
                if len(parsed) != 1 or parsed[0][1].get("corporate_event_id") != event["id"]:
                    raise BookError("corporate_movement_mismatch", "Una fila de pago/split para ASSET y EVENT; el resto usa el importador del libro.")
                added, _ = BookService.merge_entries(context, parsed, body.source, body.source_account)
                entries += added
                if not added:
                    raise BookError("corporate_already_imported", "El movimiento ya está importado. Elige enlazar o revisar el existente.")
                updates = prepare_applications(context, entries, added, {body.event_id: body.review})
                updated = next(a for a in updates if a["event_id"] == body.event_id)
            else:
                updated = application(event, body.review.model_dump(), entries, body.source, body.source_account, previous)
                if body.movement_id:
                    item = next((e for e in entries if e["event"]["id"] == body.movement_id), None)
                    if not item:
                        raise BookError("corporate_movement_unknown", "Movimiento efectivo no encontrado.")
                    updated = link_movement(updated, item)
                elif updated["movement_key"]:
                    item = next((e for e in entries if e["event"]["external_key"] == updated["movement_key"]), None)
                    if not item:
                        raise BookError("corporate_dependency_changed", "Movimiento vinculado ausente.")
                    updated = link_movement(updated, item)
                elif event["event_type"] == "split":
                    raise BookError("corporate_split_movement", "El split requiere crear o enlazar su movimiento.")
        apps[body.event_id] = updated
        validate_dependencies(list(apps.values()), entries)
        self.books._balance(entries, day)
        next_revision = context["portfolio"]["revision"]+1
        updated["portfolio_revision"] = next_revision
        proposed = {**context, "entries": entries, "applications": list(apps.values()),
                    "portfolio": {**context["portfolio"], "revision": next_revision}}
        result = self._portfolio(proposed, day, body.offset, body.limit)
        token = self._token("application", context, body)
        document = self._document("application", body, result, ident, context=context["portfolio"]["revision"])
        if body.commit:
            self._check_token(token, body)
            def save(work):
                current = self._portfolio_context(work, ident)
                if fingerprint(current) != fingerprint(context):
                    raise RevisionConflict("Libro, catálogo, evento o precios cambiaron durante la revisión; no se ha confirmado.")
                for entry in added:
                    work.insert_native_entry(ident, entry)
                work.write_portfolio_revision(ident, [e["event"]["id"] for e in sorted(entries, key=lambda e: (e["date"], e["day_sequence"]))], context["portfolio"]["bindings"])
                work.save_corporate_application(ident, next_revision, updated)
                work.bind_book_source(ident, body.source, body.source_account)
                work.save_corporate_document(document)
                work.audit("corporate.application_confirmed", ident, dict(event_id=body.event_id, document_id=document["id"], revision=next_revision))
            self.store.atomic(save)
        return {**result, "committed": body.commit, "preview_token": token, "document_id": document["id"]}

    def documents(self, ident=None, offset=0, limit=100, document_id=None):
        def read(work):
            if ident is not None:
                BookService._context(work, ident)
            if document_id:
                doc = work.corporate_document(document_id)
                if not doc or doc["portfolio_id"] != ident:
                    raise IdentityNotFound("Documento de evento no encontrado.")
                return doc
            total, docs = work.corporate_documents(ident, offset, limit)
            summaries = [{k: doc[k] for k in ("id", "portfolio_id", "kind", "created_at")} for doc in docs]
            return dict(total=total, documents=summaries, offset=offset, limit=limit)
        return self.store.atomic(read)

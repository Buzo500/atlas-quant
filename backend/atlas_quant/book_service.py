"""D4 application cases: coherent read, pure calculation, revision-checked commit."""
from datetime import datetime, timezone
import hashlib
import hmac

from .book import (POLICY, BookError, balance, cutoff, parse_movements, parse_statement,
                   reconcile, resolve_mapping, text_field)
from .catalog import IdentityNotFound, RevisionConflict
from .portfolios import fingerprint


def payload(body):
    return body.model_dump(exclude={"expected_revision", "commit", "preview_token", "offset", "limit"})


def economic(item):
    event = item["event"]
    return {k: v for k, v in event.items() if k not in {
        "id", "external_key", "revision", "source_row", "corrects", "voided"}}


class BookService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _context(work, ident, revision=None, *, history=False):
        try:
            portfolio = work.portfolio_record(ident, revision)
        except KeyError as exc:
            raise IdentityNotFound(exc.args[0]) from exc
        catalog = work.catalog(portfolio["catalog_revision"]) if revision is not None and portfolio["catalog_revision"] else work.catalog()
        result = dict(portfolio=portfolio, catalog=catalog, entries=work.portfolio_events(portfolio),
                      sources=work.book_sources(ident))
        if revision is not None:
            sources = {(e["event"]["source"], e["event"]["source_account"])
                       for e in result["entries"] if "source_account" in e["event"]}
            result["sources"] = [dict(source=source, source_account=account) for source, account in sorted(sources)]
        if history:
            result["all_entries"] = work.native_entries(ident)
        return result

    @staticmethod
    def _cut(context, day):
        p = context["portfolio"]
        return dict(portfolio_id=p["id"], portfolio_revision=p["revision"],
                    catalog_revision=context["catalog"]["revision"],
                    accounting_policy=p["accounting_policy"], as_of_date=day)

    def _detail(self, context, day, offset=0, limit=100):
        entries = sorted((e for e in context["entries"] if e["date"] <= day),
                         key=lambda e: (e["date"], e["day_sequence"]))
        return dict(context=self._cut(context, day),
                    balance=balance(entries, day, context["portfolio"]["accounting_policy"]),
                    entries=entries[offset:offset+limit], total=len(entries), offset=offset, limit=limit,
                    sources=context["sources"])

    def read(self, ident, as_of_date=None, revision=None, offset=0, limit=100):
        day = cutoff(as_of_date or datetime.now(timezone.utc).date().isoformat())
        context = self.store.atomic(lambda work: self._context(work, ident, revision))
        return self._detail(context, day, offset, limit)

    @staticmethod
    def _native(context):
        if context["portfolio"]["accounting_policy"] != POLICY:
            raise BookError("unsupported_accounting_policy",
                            "CSV v2 y correcciones nativas requieren una cartera con libro v2. La cartera heredada conserva su CSV v1 y puede conciliar extractos.")

    @staticmethod
    def _revision(context, expected):
        if context["portfolio"]["revision"] != expected:
            raise RevisionConflict("La cartera ha cambiado. Actualiza y previsualiza de nuevo.")

    @staticmethod
    def _source(context, source, account):
        text_field(source, "source")
        text_field(account, "source_account")
        for known in context["sources"]:
            if known["source"] == source and known["source_account"] != account:
                raise BookError("account_mismatch", "Esta fuente está vinculada a otra cuenta externa de la cartera.")

    @staticmethod
    def _entry(event, source, account, line, revision=1, corrects=None, voided=False):
        key = fingerprint([source, account, event["external_id"]])
        event = {**event, "source": source, "source_account": account, "source_row": line,
                 "external_key": key, "revision": revision, "corrects": corrects, "voided": voided,
                 "id": fingerprint([key, revision])}
        return dict(event=event, listing_id=event["listing_id"], date=event["date"],
                    day_sequence=event["day_sequence"])

    @staticmethod
    def _token(kind, original, body):
        return fingerprint(dict(purpose="atlas-book-" + kind, context=original, payload=payload(body)))

    def _commit(self, ident, kind, context, body, token, document, new_entries, effective, *, history):
        if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
            raise RevisionConflict("Previsualización ausente u obsoleta. Revisa el lote de nuevo.")
        original = fingerprint(context)
        def save(work):
            current = self._context(work, ident, history=history)
            if fingerprint(current) != original:
                raise RevisionConflict("El contexto cambió durante el cálculo. No se ha confirmado el lote.")
            previous = work.book_document(ident, document["id"])
            if previous is not None:
                return current["portfolio"]["revision"]
            for item in new_entries:
                work.insert_native_entry(ident, item)
            if new_entries:
                ordered = sorted(effective, key=lambda e: (e["date"], e["day_sequence"]))
                work.write_portfolio_revision(ident, [e["event"]["id"] for e in ordered], current["portfolio"]["bindings"])
            work.bind_book_source(ident, document["source"], document["source_account"])
            revision = work.portfolio_record(ident)["revision"]
            saved = {**document, "portfolio_revision": revision}
            work.save_book_document(ident, saved)
            work.audit("book." + kind + "_confirmed", ident,
                       dict(document_id=saved["id"], previous_revision=current["portfolio"]["revision"],
                            revision=revision, added=saved["added"], status=saved["status"]))
            return revision
        return self.store.atomic(save)

    @staticmethod
    def _document(kind, ident, context, day, source, account, body, result, document_id):
        data = payload(body)
        if "csv" in data:
            data["csv_sha256"] = hashlib.sha256(data["csv"].encode()).hexdigest()
        return dict(id=document_id, kind=kind, portfolio_revision=context["portfolio"]["revision"],
                    catalog_revision=context["catalog"]["revision"], as_of_date=day, source=source,
                    source_account=account, created_at=datetime.now(timezone.utc).isoformat(),
                    status=result.get("status", "recorded"), added=result.get("added", 0),
                    duplicates=result.get("duplicates", 0), evidence=data,
                    balance=result["balance"], differences=result.get("differences", []))

    def import_movements(self, ident, body):
        context = self.store.atomic(lambda work: self._context(work, ident, history=True))
        self._revision(context, body.expected_revision)
        self._native(context)
        self._source(context, body.source, body.source_account)
        mapping = resolve_mapping(body.mapping, context["catalog"])
        parsed = parse_movements(body.csv, mapping, body.as_of_date, body.gross_explanations)
        known = {}
        for item in context["all_entries"]:
            key = item["event"]["external_key"]
            if key not in known or item["event"]["revision"] > known[key]["event"]["revision"]:
                known[key] = item
        added, duplicates = [], 0
        for line, event in parsed:
            item = self._entry(event, body.source, body.source_account, line)
            key = item["event"]["external_key"]
            if key in known:
                if economic(known[key]) != economic(item):
                    raise BookError("duplicate_conflict", "El ID externo ya existe con contenido distinto. Usa una corrección revisada.", line, "external_id")
                duplicates += 1
            else:
                added.append(item)
                known[key] = item
        effective = context["entries"] + added
        # Validate later history too, even when the submitted cut is earlier.
        last = max([body.as_of_date] + [e["date"] for e in effective])
        balance(effective, last)
        result = self._detail({**context, "entries": effective}, body.as_of_date, body.offset, body.limit)
        token = self._token("import", context, body)
        document_id = fingerprint(dict(kind="import", portfolio=ident, payload=payload(body)))
        last_existing = max(((e["date"], e["day_sequence"]) for e in context["entries"]), default=("", 0))
        result.update(added=len(added), duplicates=duplicates,
                      historical_insertion=any((e["date"], e["day_sequence"]) < last_existing for e in added))
        document = self._document("import", ident, context, body.as_of_date, body.source, body.source_account, body, result, document_id)
        if body.commit:
            result["context"]["portfolio_revision"] = self._commit(ident, "import", context, body, token, document, added, effective, history=True)
        return {**result, "committed": body.commit, "preview_token": token, "document_id": document_id}

    def reconcile(self, ident, body):
        context = self.store.atomic(lambda work: self._context(work, ident))
        self._revision(context, body.expected_revision)
        self._source(context, body.source, body.source_account)
        mapping = resolve_mapping(body.mapping, context["catalog"])
        reference = parse_statement(body.csv, mapping, body.as_of_date)
        book = balance(context["entries"], body.as_of_date, context["portfolio"]["accounting_policy"])
        differences = reconcile(book, reference)
        status = "matched" if all(row["matched"] for row in differences) else "differences"
        token = self._token("reconciliation", context, body)
        document_id = fingerprint(dict(kind="reconciliation", portfolio=ident, revision=context["portfolio"]["revision"],
                                       catalog_revision=context["catalog"]["revision"], payload=payload(body)))
        result = dict(context=self._cut(context, body.as_of_date), balance=book, differences=differences, status=status)
        document = self._document("reconciliation", ident, context, body.as_of_date, body.source, body.source_account, body, result, document_id)
        if body.commit:
            self._commit(ident, "reconciliation", context, body, token, document, [], context["entries"], history=False)
        return {**result, "differences": differences[body.offset:body.offset+body.limit],
                "total": len(differences), "offset": body.offset, "limit": body.limit,
                "committed": body.commit, "preview_token": token, "document_id": document_id}

    def correct(self, ident, body):
        context = self.store.atomic(lambda work: self._context(work, ident, history=True))
        self._revision(context, body.expected_revision)
        self._native(context)
        old = next((e for e in context["entries"] if e["event"]["id"] == body.event_id), None)
        if old is None:
            raise BookError("correction_target", "Movimiento no efectivo o inexistente en esta revisión.")
        original = old["event"]
        source, account = original["source"], original["source_account"]
        self._source(context, source, account)
        if body.action == "void":
            if body.csv or body.mapping or body.gross_explanations:
                raise BookError("incompatible_field", "Anular no admite CSV, mapeo ni explicaciones de sustitución.")
            event, line = economic(old), original["source_row"]
        else:
            mapping = resolve_mapping(body.mapping, context["catalog"])
            parsed = parse_movements(body.csv, mapping, datetime.now(timezone.utc).date().isoformat(), body.gross_explanations)
            if len(parsed) != 1 or parsed[0][1]["external_id"] != original["external_id"]:
                raise BookError("correction_target", "La sustitución requiere una fila con el mismo ID externo.")
            line, event = parsed[0]
        replacement = self._entry(event, source, account, line, original["revision"]+1,
                                  original["id"], body.action == "void")
        effective = [e for e in context["entries"] if e["event"]["id"] != body.event_id]
        if body.action == "replace":
            effective.append(replacement)
        day = datetime.now(timezone.utc).date().isoformat()
        result = self._detail({**context, "entries": effective}, day, body.offset, body.limit)
        result.update(added=0, duplicates=0, historical_insertion=True)
        token = self._token("correction", context, body)
        document_id = fingerprint(dict(kind="correction", portfolio=ident, revision=context["portfolio"]["revision"], payload=payload(body)))
        document = self._document("correction", ident, context, day, source, account, body, result, document_id)
        if body.commit:
            result["context"]["portfolio_revision"] = self._commit(ident, "correction", context, body, token, document, [replacement], effective, history=True)
        return {**result, "committed": body.commit, "preview_token": token, "document_id": document_id}

    def documents(self, ident, offset=0, limit=100, document_id=None):
        def read(work):
            context = self._context(work, ident)
            if document_id is not None:
                document = work.book_document(ident, document_id)
                if document is None:
                    raise IdentityNotFound("Documento no encontrado en esta cartera.")
                document["current"] = (document["portfolio_revision"] == context["portfolio"]["revision"]
                                       and document["catalog_revision"] == context["catalog"]["revision"])
                return document
            total, documents = work.book_documents(ident, offset, limit)
            summaries = []
            for document in documents:
                summary = {k: v for k, v in document.items() if k not in {"evidence", "balance", "differences"}}
                summary["current"] = (document["portfolio_revision"] == context["portfolio"]["revision"]
                                      and document["catalog_revision"] == context["catalog"]["revision"])
                summaries.append(summary)
            return dict(total=total, documents=summaries, offset=offset, limit=limit)
        return self.store.atomic(read)

"""Review and commit quality evidence or explicit historical price revisions."""
from copy import deepcopy
import hmac

from .catalog import IdentityNotFound, RevisionConflict
from .data import parse_prices_csv
from .quality import EvidenceInput, digest, prepare_evidence, report


class QualityService:
    def __init__(self, store):
        self.store = store

    def read(self, ident, version, symbol, **options):
        dataset = self.store.get_dataset_version(ident, version)
        if dataset is None:
            raise IdentityNotFound("Versión de precios no encontrada.")
        return report(dataset, symbol, **options)

    def _current(self, ident, version):
        dataset = self.store.get("dataset", ident)
        if dataset is None:
            raise IdentityNotFound("Conjunto de datos no encontrado.")
        if dataset["version"] != version:
            raise RevisionConflict("La versión ha cambiado. Revisa de nuevo el conjunto.")
        return dataset

    def _confirm(self, current, updated, body, payload, event, *, revision=False):
        token = digest(dict(purpose=event, current=current, payload=payload))
        if body.commit:
            if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
                raise RevisionConflict("Previsualización ausente u obsoleta. Vuelve a revisar.")
            def save(work):
                latest = work.get("dataset", current["id"])
                if digest(latest) != digest(current):
                    raise RevisionConflict("Los datos han cambiado durante la revisión.")
                result = work.save_dataset(updated, allow_revision=revision)
                work.audit(event, current["id"], {"previous_version": current["version"],
                    "version": result["version"], "reason": payload.get("reason"), "evidence_hash": digest(payload)})
                return result
            updated = self.store.atomic(save)
        return updated, token

    def evidence(self, ident, body):
        current = self._current(ident, body.expected_version)
        evidence = prepare_evidence(EvidenceInput.model_validate(body.model_dump(exclude={"expected_version", "commit", "preview_token"})), current)
        updated = deepcopy(current)
        updated.setdefault("quality_evidence", {})[evidence["symbol"]] = evidence
        preview = report(updated, evidence["symbol"])
        updated, token = self._confirm(current, updated, body, evidence, "dataset.quality_reviewed")
        preview["dataset_version"] = updated["version"]
        return dict(dataset_id=ident, version=updated["version"], committed=body.commit,
                    preview_token=token, quality=preview)

    def revise(self, ident, body):
        from datetime import datetime, timezone
        current = self._current(ident, body.expected_version)
        bars = parse_prices_csv(body.csv)
        if len(bars) > 100_000 or any(b["date"] > datetime.now(timezone.utc).date().isoformat() for b in bars):
            raise ValueError("Máximo 100.000 barras y ninguna fecha futura.")
        old = {(b["date"], b["symbol"]): b for b in current["bars"]}
        new = {(b["date"], b["symbol"]): b for b in bars}
        if not old.keys() <= new.keys():
            raise ValueError("La revisión completa debe conservar todas las fechas y símbolos anteriores.")
        if any(new[key].get("currency", "EUR") != old[key].get("currency", "EUR") for key in old):
            raise ValueError("Una revisión no puede cambiar la moneda.")
        changed = [key for key in old if old[key] != new[key]]
        added = new.keys() - old.keys()
        if not changed and not added:
            raise ValueError("No hay precios corregidos ni barras nuevas.")
        affected = {key[1] for key in [*changed, *added]}
        updated = {**deepcopy(current), "bars": bars}
        updated["quality_evidence"] = {s: e for s, e in current.get("quality_evidence", {}).items() if s not in affected}
        if updated.get("feed"):
            updated["restored_feed"] = updated.pop("feed")
        updated["price_revision"] = dict(reason=body.reason, previous_version=current["version"])
        payload = dict(reason=body.reason, bars=bars)
        updated, token = self._confirm(current, updated, body, payload, "dataset.prices_revised", revision=True)
        return dict(dataset_id=ident, version=updated["version"], committed=body.commit,
                    preview_token=token, changed=len(changed), added=len(added),
                    affected_symbols=sorted(affected), feed_paused=bool(current.get("feed")))

"""Pure corporate-event validation and effects; no persistence or provider calls."""
from datetime import datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
from math import gcd
import re

from .book import BookError, rows, number, text_field, decimal_text, bounded, CENT, cutoff
from .analytics import iso_date
from .portfolios import fingerprint

EVENT_FORMAT = "atlas-corporate-events-v1"
EVENT_COLUMNS = ("external_id,event_type,listing_ref,effective_date,payment_date,available_at,"
                 "gross_per_unit,currency,ratio_numerator,ratio_denominator,source_reference").split(",")


def ratio(numerator, denominator, row=None):
    values = []
    for name, value in (("ratio_numerator", numerator), ("ratio_denominator", denominator)):
        if not re.fullmatch(r"[1-9][0-9]{0,9}", str(value)) or int(value) > 1_000_000_000:
            raise BookError("invalid_ratio", "Ratio: enteros entre 1 y 1.000.000.000.", row, name)
        values.append(int(value))
    common = gcd(*values)
    return values[0] // common, values[1] // common


def split_quantity(quantity, numerator, denominator, evidence):
    n, d = ratio(numerator, denominator)
    exact = Fraction(quantity) * Fraction(n, d)
    if (exact * 10**12).denominator != 1:
        raise BookError("fraction_unresolved", "La fracción no es representable exactamente con 12 decimales; no se redondea.")
    if exact.denominator != 1:
        text_field(evidence, "fraction_evidence", limit=500)
    with localcontext() as ctx:
        ctx.prec = 64
        return bounded(Decimal(exact.numerator) / Decimal(exact.denominator), "quantity")


def optional_date(value, field, row):
    if not value:
        return None
    try:
        return iso_date(value)
    except ValueError as exc:
        raise BookError("invalid_date", str(exc), row, field) from exc


def parse_events(csv, mapping, verified=False, evidence=""):
    if verified:
        evidence = text_field(evidence, "evidence", limit=500)
    result = []
    for line, raw in rows(csv, EVENT_COLUMNS):
        external = text_field(raw["external_id"], "external_id", line)
        ident = mapping.get(raw["listing_ref"])
        if not ident:
            raise BookError("identity_unknown", "Mapea explícitamente la cotización del evento.", line, "listing_ref")
        kind = raw["event_type"]
        if kind not in {"dividend", "split"} or raw["currency"] != "EUR":
            raise BookError("unsupported_corporate_event", "D5 admite dividendos ordinarios y splits EUR.", line)
        effective = optional_date(raw["effective_date"], "effective_date", line)
        payment = optional_date(raw["payment_date"], "payment_date", line)
        available = raw["available_at"] or None
        if available:
            try:
                value = datetime.fromisoformat(available.replace("Z", "+00:00"))
                if value.tzinfo is None or value.utcoffset() is None or value > datetime.now(timezone.utc):
                    raise ValueError()
                available = value.astimezone(timezone.utc).isoformat()
            except ValueError as exc:
                raise BookError("invalid_availability", "Disponibilidad UTC verificada, con zona horaria y no futura.", line, "available_at") from exc
        if payment and effective and payment < effective:
            raise BookError("corporate_dates", "Pago anterior a exfecha fuera del alcance ordinario; revisa la evidencia.", line)
        gross, n, d = None, None, None
        if kind == "dividend":
            gross = decimal_text(number(raw["gross_per_unit"], "gross_per_unit", 12, line, positive=True))
            if raw["ratio_numerator"] or raw["ratio_denominator"]:
                raise BookError("incompatible_field", "Un dividendo no admite ratio.", line)
        else:
            if payment or raw["gross_per_unit"]:
                raise BookError("incompatible_field", "Un split no admite campos de pago.", line)
            n, d = ratio(raw["ratio_numerator"], raw["ratio_denominator"], line)
        reference = text_field(raw["source_reference"], "source_reference", line, 500)
        result.append((line, external, dict(listing_id=ident, event_type=kind, effective_date=effective,
            payment_date=payment, available_at=available, gross_per_unit=gross, currency="EUR",
            ratio_numerator=n, ratio_denominator=d, source_reference=reference,
            verified=verified, evidence=evidence, cancelled=False)))
    return result


def event_economics(event):
    return {k: event[k] for k in ("listing_id", "event_type", "effective_date", "payment_date",
            "gross_per_unit", "currency", "ratio_numerator", "ratio_denominator")}


def event_for(state, ident, revision=None):
    event = next((e for e in state["events"] if e["id"] == ident), None)
    if not event:
        raise BookError("corporate_event_unknown", "Evento corporativo no encontrado.")
    if revision is not None and event["revision"] != revision:
        raise BookError("corporate_revision", "La revisión del evento cambió; revisa la aplicación.")
    if event["cancelled"] or not event["verified"] or not event["effective_date"]:
        raise BookError("corporate_action_unresolved", "El evento necesita evidencia verificada y fecha efectiva, y no puede estar cancelado.")
    cutoff(event["effective_date"])
    return event


def movement_options(context, body):
    events = {}
    for ref, ident in body.corporate_mapping.items():
        events[ref] = event_for(context["corporate"], ident)
    return dict(corporate=events, unaccredited=body.unaccredited_payments,
                reviews={k: v.model_dump() for k, v in body.corporate_reviews.items()})


def basis(entries, event, sequence):
    boundary = event["effective_date"], sequence
    prefix = sorted((e for e in entries if e["listing_id"] == event["listing_id"]
        and e["event"]["kind"] in {"buy", "sell", "split"}
        and (e["date"], e["day_sequence"]) < boundary), key=lambda e: (e["date"], e["day_sequence"]))
    quantity = Decimal(0)
    with localcontext() as ctx:
        ctx.prec = 64
        for entry in prefix:
            value = entry["event"]
            if value["kind"] == "split":
                quantity = split_quantity(quantity, value["ratio_numerator"], value["ratio_denominator"], value["fraction_evidence"])
            else:
                quantity += Decimal(value["quantity"]) * (1 if value["kind"] == "buy" else -1)
    return quantity, fingerprint(prefix)


def application(event, review, entries, source, account, previous=None):
    if review["event_revision"] != event["revision"]:
        raise BookError("corporate_revision", "La revisión solicitada no es la vigente.")
    evidence = text_field(review["evidence"], "evidence", limit=500)
    quantity, basis_hash = basis(entries, event, review["day_sequence"])
    eligible, gross = None, None
    if event["event_type"] == "dividend":
        if any(e["listing_id"] == event["listing_id"] and e["date"] == event["effective_date"]
               and e["day_sequence"] == review["day_sequence"] and e["event"]["kind"] in {"buy", "sell", "split"} for e in entries):
            raise BookError("event_order_ambiguous", "El derecho comparte secuencia con una operación; declara su orden efectivo.")
        eligible = number(review["eligible_quantity"], "eligible_quantity", 12, None, positive=True)
        if eligible != quantity:
            text_field(review["discrepancy_reason"], "discrepancy_reason", limit=500)
        with localcontext() as ctx:
            ctx.prec, ctx.rounding = 64, ROUND_HALF_EVEN
            gross = bounded(eligible * Decimal(event["gross_per_unit"]), "dividend_gross").quantize(CENT)
        if review["gross_amount"] is not None:
            declared = number(review["gross_amount"], "gross_amount", 2, None, positive=True)
            if declared != gross:
                text_field(review["gross_explanation"], "gross_explanation", limit=500)
            gross = declared
    elif review["eligible_quantity"] is not None or review["gross_amount"] is not None:
        raise BookError("incompatible_field", "Un split no admite elegibilidad o bruto de dividendo.")
    return dict(event_id=event["id"], event_revision=event["revision"], revision=(previous["revision"] if previous else 0)+1,
        portfolio_revision=0, source=source, source_account=account, event_type=event["event_type"],
        effective_date=event["effective_date"], day_sequence=review["day_sequence"],
        eligible_quantity=decimal_text(eligible) if eligible is not None else None, basis_quantity=decimal_text(quantity),
        basis_hash=basis_hash, gross_amount=decimal_text(gross, money=True) if gross is not None else None,
        evidence=evidence, discrepancy_reason=review["discrepancy_reason"], gross_explanation=review["gross_explanation"],
        fraction_evidence=review["fraction_evidence"], event_snapshot=event,
        movement_key=previous["movement_key"] if previous and not previous["cancelled"] else None,
        movement_fingerprint=previous["movement_fingerprint"] if previous and not previous["cancelled"] else None,
        cancelled=False)


def link_movement(app, item):
    value, event = item["event"], app["event_snapshot"]
    if value.get("corporate_event_id") not in (None, event["id"]):
        raise BookError("corporate_movement_mismatch", "El movimiento identifica otro evento; corrige su referencia antes de enlazarlo.")
    if item["listing_id"] != event["listing_id"] or (value["source"], value["source_account"]) != (app["source"], app["source_account"]):
        raise BookError("corporate_movement_mismatch", "Movimiento de otra cotización, fuente o cuenta.")
    if app["event_type"] == "dividend":
        if value["kind"] != "dividend_payment" or Decimal(value["gross_amount"]) != Decimal(app["gross_amount"]):
            raise BookError("corporate_payment_difference", "El pago completo debe coincidir con el derecho bruto; no se ajusta la diferencia.")
        if item["date"] < app["effective_date"] or (event["payment_date"] and item["date"] != event["payment_date"]):
            raise BookError("corporate_payment_date", "La fecha del movimiento no coincide con el pago acreditado.")
    elif (value["kind"] != "split" or item["date"] != app["effective_date"]
          or item["day_sequence"] != app["day_sequence"]
          or ratio(value["ratio_numerator"], value["ratio_denominator"]) != ratio(event["ratio_numerator"], event["ratio_denominator"])):
        raise BookError("corporate_split_difference", "El movimiento no coincide con la fecha, secuencia y ratio del split.")
    if app["movement_key"] not in (None, value["external_key"]):
        raise BookError("corporate_duplicate", "El evento ya tiene un movimiento vinculado; revisa su corrección.")
    return {**app, "movement_key": value["external_key"], "movement_fingerprint": fingerprint(item)}


def validate_dependencies(applications, entries):
    movements = {e["event"]["external_key"]: e for e in entries}
    claimed = set()
    for app in applications:
        if app["cancelled"]:
            continue
        _, current_hash = basis(entries, app["event_snapshot"], app["day_sequence"])
        if current_hash != app["basis_hash"]:
            raise BookError("corporate_dependency_changed", "La historia modifica la base de un evento confirmado. Revisa sus dependencias antes de confirmar; no se ha escrito nada.")
        key = app["movement_key"]
        if key is not None:
            item = movements.get(key)
            if key in claimed or not item or fingerprint(item) != app["movement_fingerprint"]:
                raise BookError("corporate_dependency_changed", "Un movimiento vinculado cambió o se utiliza dos veces; requiere revisión conjunta.")
            link_movement(app, item)
            claimed.add(key)


def prepare_applications(context, entries, changed, reviews):
    """New/replaced corporate entries and their application form one commit."""
    apps = {a["event_id"]: a for a in context["applications"]}
    updates = {}
    for item in changed:
        value = item["event"]
        old = next((a for a in apps.values() if not a["cancelled"] and a["movement_key"] == value["external_key"]), None)
        if value.get("voided"):
            if old:
                app = {**old, "revision": old["revision"]+1, "movement_key": None, "movement_fingerprint": None,
                       "cancelled": old["event_type"] == "split"}
                apps[app["event_id"]] = updates[app["event_id"]] = app
            continue
        ident = value.get("corporate_event_id") or (old["event_id"] if old else None)
        if ident is None:
            continue
        event = event_for(context["corporate"], ident)
        previous = apps.get(ident)
        review = reviews.get(ident)
        if review:
            app = application(event, review.model_dump() if hasattr(review, "model_dump") else review,
                              entries, value["source"], value["source_account"], previous)
        elif previous and not previous["cancelled"] and previous["event_revision"] == event["revision"]:
            app = {**previous, "revision": previous["revision"]+1}
        else:
            raise BookError("corporate_review_required", "Revisa elegibilidad/secuencia y evidencia de este evento antes de aplicarlo.")
        app = link_movement(app, item)
        apps[ident] = updates[ident] = app
    for ident, review in reviews.items():
        if ident in updates:
            continue
        previous = apps.get(ident)
        if not previous or previous["cancelled"]:
            raise BookError("corporate_review_unused", "Revisión sin evento aplicado o movimiento correspondiente.")
        event = event_for(context["corporate"], ident)
        app = application(event, review.model_dump() if hasattr(review, "model_dump") else review,
                          entries, previous["source"], previous["source_account"], previous)
        if app["movement_key"]:
            item = next((e for e in entries if e["event"]["external_key"] == app["movement_key"]), None)
            if not item:
                raise BookError("corporate_dependency_changed", "Movimiento vinculado ausente.")
            app = link_movement(app, item)
        apps[ident] = updates[ident] = app
    validate_dependencies(list(apps.values()), entries)
    return list(updates.values())

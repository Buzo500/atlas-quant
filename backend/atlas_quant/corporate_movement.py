"""The two D5 rows of atlas-ledger-v2; called by the shared book parser."""
from .book import BookError, number, decimal_text, text_field, listing
from .corporate import ratio


def parse(raw, line, mapping, corporate, unaccredited, reviews, *, multicurrency=False):
    kind, external = raw["kind"], raw["external_id"]
    ident = listing(raw["listing_ref"], mapping, line)
    reference = raw["corporate_event_ref"]
    event = corporate.get(reference) if reference else None
    if (reference and event is None) or (kind == "split" and event is None):
        raise BookError("corporate_event_unknown", "Mapea la referencia corporativa a un evento revisado.", line, "corporate_event_ref")
    if event and (event["listing_id"] != ident or event["event_type"] != ("dividend" if kind == "dividend_payment" else "split")):
        raise BookError("corporate_movement_mismatch", "Tipo o cotización incompatible con el evento.", line)
    currency = raw['currency']
    if currency not in (('EUR', 'USD') if multicurrency else ('EUR',)):
        raise BookError("unsupported_currency", "D5 solo admite EUR.", line)
    if event and event['currency'] != currency:
        raise BookError('currency_mismatch', 'El pago/split debe conservar la moneda del evento.', line)
    forbidden = ["quantity", "unit_price", "fx_to_amount", "fx_to_currency"]
    result = dict(external_id=external, date=raw["date"], day_sequence=int(raw["day_sequence"]),
                  kind=kind, listing_id=ident, currency=currency, quantity=None, unit_price=None,
                  gross_explanation=None, corporate_event_id=event["id"] if event else None)
    if kind == "dividend_payment":
        forbidden += ["ratio_numerator", "ratio_denominator"]
        if raw["fee_currency"] != currency or raw["tax_currency"] != currency:
            raise BookError("unsupported_currency", "Comisión y retención deben declarar la moneda del cobro.", line)
        gross = number(raw["gross_amount"], "gross_amount", 2, line, positive=True)
        fee = number(raw["fee_amount"], "fee_amount", 2, line)
        tax = number(raw["tax_amount"], "tax_amount", 2, line)
        if gross - tax - fee < 0:
            raise BookError("corporate_net_negative", "El dividendo ordinario no admite neto negativo.", line)
        note = "" if event else text_field(unaccredited.get(external, ""), "unaccredited_payment_evidence", line, 500)
        result.update(gross_amount=decimal_text(gross, money=True), fee_amount=decimal_text(fee, money=True),
                      tax_amount=decimal_text(tax, money=True), unaccredited_evidence=note)
    else:
        forbidden += ["gross_amount", "fee_amount", "fee_currency", "tax_amount", "tax_currency"]
        n, d = ratio(raw["ratio_numerator"], raw["ratio_denominator"], line)
        if (n, d) != ratio(event["ratio_numerator"], event["ratio_denominator"]) or raw["date"] != event["effective_date"]:
            raise BookError("corporate_split_difference", "Fecha o ratio incompatible con el evento.", line)
        review = reviews.get(event["id"], {})
        result.update(gross_amount=None, fee_amount=None, tax_amount=None, ratio_numerator=n,
                      ratio_denominator=d, fraction_evidence=review.get("fraction_evidence", ""))
    for field in forbidden:
        if raw[field]:
            raise BookError("incompatible_field", f"{field} debe estar vacío para este tipo.", line, field)
    return result

"""Price-independent book; EUR compatibility and explicit EUR/USD balances."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN

from .analytics import iso_date

POLICY = "atlas-accounting-v2"
MOVEMENT_FORMAT = "atlas-ledger-v2"
STATEMENT_FORMAT = "atlas-statement-v2"
MOVEMENT_COLUMNS = (
    "external_id,date,day_sequence,kind,listing_ref,quantity,unit_price,gross_amount,"
    "currency,fee_amount,fee_currency,tax_amount,tax_currency,fx_to_amount,"
    "fx_to_currency,ratio_numerator,ratio_denominator,corporate_event_ref"
).split(",")
STATEMENT_COLUMNS = "as_of_date,record_type,listing_ref,currency,quantity,amount".split(",")
MAXIMUM = Decimal("1e18")
CENT = Decimal("0.01")
SCALE = Decimal("0.000000000001")
ZERO = Decimal(0)


class BookError(ValueError):
    def __init__(self, code, message, row=None, field=None):
        super().__init__(message)
        self.code, self.row, self.field = code, row, field

    def detail(self):
        return [{"type": self.code, "msg": str(self),
                 "loc": ["book"] + ([f"fila {self.row}"] if self.row else [])
                 + ([self.field] if self.field else [])}]


def decimal_text(value, *, money=False):
    """Formatting only; callers must validate scale before monetary formatting."""
    if money:
        return format(value, ".2f")
    result = format(value, "f")
    return (result.rstrip("0").rstrip(".") if "." in result else result) or "0"


def bounded(value, name, row=None):
    if not value.is_finite() or abs(value) > MAXIMUM:
        raise BookError("numeric_range", f"{name}: supera el límite absoluto de 1e18.", row, name)
    return value


def number(value, field, scale, row, *, positive=False):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise BookError("invalid_decimal", "Decimal requerido con punto, sin signo ni exponente.", row, field)
    if len(value) > 64 or ("." in value and len(value.split(".")[1]) > scale):
        raise BookError("invalid_decimal", f"Máximo {scale} decimales y 64 caracteres.", row, field)
    result = bounded(Decimal(value), field, row)
    if positive and result <= 0:
        raise BookError("invalid_decimal", "El valor debe ser positivo.", row, field)
    return result


def text_field(value, field, row=None, limit=100):
    value = value.strip()
    if not value or len(value) > limit or any(ord(c) < 32 for c in value):
        raise BookError("invalid_field", f"{field}: texto requerido, máximo {limit} caracteres sin controles.", row, field)
    return value


def cutoff(value):
    try:
        day = iso_date(value)
    except ValueError as exc:
        raise BookError("invalid_date", str(exc), field="as_of_date") from exc
    if day > datetime.now(timezone.utc).date().isoformat():
        raise BookError("future_date", "No se admite una fecha futura.", field="as_of_date")
    return day


def rows(content, columns):
    if not content or len(content) > 8_000_000:
        raise BookError("input_limit", "CSV requerido, máximo 8.000.000 caracteres.")
    try:
        content.encode("utf-8")
    except UnicodeError as exc:
        raise BookError("invalid_utf8", "El CSV debe contener texto UTF-8 válido.") from exc
    try:
        reader = csv.DictReader(io.StringIO(content.removeprefix("\ufeff")), strict=True)
        if reader.fieldnames != columns:
            raise BookError("invalid_header", "Usa la plantilla del formato seleccionado, con sus encabezados exactos.")
        count = 0
        for raw in reader:
            count += 1
            if count > 10_000:
                raise BookError("input_limit", "Máximo 10.000 filas por lote.")
            line = reader.line_num
            if None in raw or any(value is None for value in raw.values()):
                raise BookError("invalid_row", "Número de columnas incorrecto.", line)
            yield line, {key: value.strip() for key, value in raw.items()}
        if not count:
            raise BookError("empty_csv", "El CSV no contiene registros.")
    except csv.Error as exc:
        raise BookError("invalid_csv", "CSV mal formado o campo demasiado largo.") from exc


def resolve_mapping(mapping, catalog, *, multicurrency=False):
    listings = {item["id"]: item for item in catalog["listings"]}
    if len(mapping) > 100:
        raise BookError("input_limit", "Máximo 100 referencias por lote.")
    for reference, ident in mapping.items():
        text_field(reference, "listing_ref")
        if reference != reference.strip() or ident not in listings:
            raise BookError("identity_unknown", "Referencia o cotización no encontrada.", field="mapping")
        if listings[ident]["currency"] not in (("EUR", "USD") if multicurrency else ("EUR",)):
            raise BookError("unsupported_currency", "D4 solo admite cotizaciones EUR.", field="mapping")
    return mapping


def validate_currencies(parsed, catalog):
    currencies = {item['id']: item['currency'] for item in catalog['listings']}
    for row in parsed:
        line, event = row[0], row[-1]
        ident = event.get('listing_id')
        if ident is not None and currencies.get(ident) != event['currency']:
            raise BookError('currency_mismatch', 'La moneda no coincide con la cotización mapeada.', line, 'currency')


def listing(reference, mapping, row):
    if not reference or reference not in mapping:
        raise BookError("identity_unknown", "Añade un mapeo explícito para esta referencia.", row, "listing_ref")
    return mapping[reference]


def parse_movements(content, mapping, as_of_date, explanations, *, corporate=None, unaccredited=None, reviews=None, multicurrency=False):
    end = cutoff(as_of_date)
    parsed, seen = [], {}
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        for line, raw in rows(content, MOVEMENT_COLUMNS):
            external = text_field(raw["external_id"], "external_id", line)
            try:
                day = iso_date(raw["date"])
            except ValueError as exc:
                raise BookError("invalid_date", str(exc), line, "date") from exc
            if day > end:
                raise BookError("future_date", "Movimiento posterior al corte del lote.", line, "date")
            if not re.fullmatch(r"[1-9][0-9]{0,8}", raw["day_sequence"]):
                raise BookError("event_order_ambiguous", "Secuencia positiva explícita requerida (máximo 9 cifras).", line, "day_sequence")
            kind = raw["kind"]
            if kind in {"dividend_payment", "split"}:
                from .corporate_movement import parse
                event = parse(raw, line, mapping, corporate or {}, unaccredited or {}, reviews or {}, multicurrency=multicurrency)
                if external in explanations:
                    raise BookError("incompatible_field", "El bruto corporativo se revisa en el derecho del evento.", line)
                if external in seen and seen[external] != event:
                    raise BookError("duplicate_conflict", "Un ID externo aparece con contenido diferente.", line, "external_id")
                seen[external] = event
                parsed.append((line, event))
                continue
            if kind == 'fx_exchange' and multicurrency:
                event = parse_exchange(raw, line)
                if external in explanations:
                    raise BookError('incompatible_field', 'La conversión usa importes reales, sin explicación de precio.', line)
                if external in seen and seen[external] != event:
                    raise BookError('duplicate_conflict', 'Un ID externo aparece con contenido diferente.', line)
                seen[external] = event
                parsed.append((line, event))
                continue
            if kind not in {"deposit", "withdrawal", "buy", "sell", "fee"}:
                raise BookError("unsupported_kind", "Tipo no soportado; FX corresponde a D6.", line, "kind")
            currency = raw['currency']
            if currency not in (("EUR", "USD") if multicurrency else ("EUR",)) or raw['fee_currency'] != currency or raw['tax_currency'] != currency:
                raise BookError("unsupported_currency", "Moneda admitida y cargos en la misma moneda requeridos.", line, "currency")
            fee = number(raw["fee_amount"], "fee_amount", 2, line)
            tax = number(raw["tax_amount"], "tax_amount", 2, line)
            gross = number(raw["gross_amount"], "gross_amount", 2, line, positive=kind not in {"buy", "sell"})
            forbidden = ["fx_to_amount", "fx_to_currency", "ratio_numerator", "ratio_denominator", "corporate_event_ref"]
            if tax != 0:
                raise BookError("unsupported_tax", "Los tipos de D4 requieren retención cero explícita.", line, "tax_amount")
            if kind not in {"buy", "sell"}:
                forbidden += ["listing_ref", "quantity", "unit_price"]
            for field in forbidden:
                if raw[field]:
                    raise BookError("incompatible_field", f"{field} debe estar vacío para este tipo.", line, field)
            if kind == "fee" and fee:
                raise BookError("incompatible_field", "fee usa gross_amount y fee_amount=0 para no duplicar el cargo.", line, "fee_amount")
            listing_id, quantity, price, explanation = None, None, None, None
            if kind in {"buy", "sell"}:
                listing_id = listing(raw["listing_ref"], mapping, line)
                quantity = number(raw["quantity"], "quantity", 12, line, positive=True)
                price = number(raw["unit_price"], "unit_price", 12, line, positive=True)
                calculated = bounded(quantity * price, "quantity × unit_price", line).quantize(CENT)
                if gross != calculated:
                    explanation = text_field(explanations.get(external, ""), "gross_explanation", line, 500)
            event = dict(external_id=external, date=day, day_sequence=int(raw["day_sequence"]), kind=kind,
                         listing_id=listing_id, currency=currency,
                         quantity=decimal_text(quantity) if quantity is not None else None,
                         unit_price=decimal_text(price) if price is not None else None,
                         gross_amount=decimal_text(gross, money=True), fee_amount=decimal_text(fee, money=True),
                         tax_amount="0.00", gross_explanation=explanation)
            if external in seen and seen[external] != event:
                raise BookError("duplicate_conflict", "Un ID externo aparece con contenido diferente.", line, "external_id")
            seen[external] = event
            parsed.append((line, event))
    if set(explanations) - seen.keys():
        raise BookError("unknown_explanation", "Hay explicaciones para IDs ausentes del CSV.")
    return parsed


def parse_exchange(raw, line):
    currency, target = raw['currency'], raw['fx_to_currency']
    if {currency, target} != {'EUR', 'USD'} or raw['fee_currency'] not in {'EUR', 'USD'}:
        raise BookError('unsupported_currency', 'Conversión explícita EUR/USD y comisión en una de sus monedas.', line)
    for field in ('listing_ref', 'quantity', 'unit_price', 'tax_amount', 'tax_currency', 'ratio_numerator', 'ratio_denominator', 'corporate_event_ref'):
        if raw[field]:
            raise BookError('incompatible_field', f'{field} debe estar vacío en fx_exchange.', line, field)
    gross = number(raw['gross_amount'], 'gross_amount', 2, line, positive=True)
    received = number(raw['fx_to_amount'], 'fx_to_amount', 2, line, positive=True)
    fee = number(raw['fee_amount'], 'fee_amount', 2, line)
    return dict(external_id=raw['external_id'], date=raw['date'], day_sequence=int(raw['day_sequence']),
                kind='fx_exchange', listing_id=None, currency=currency, quantity=None, unit_price=None,
                gross_amount=decimal_text(gross, money=True), fee_amount=decimal_text(fee, money=True),
                fee_currency=raw['fee_currency'], tax_amount=None, gross_explanation=None,
                fx_to_amount=decimal_text(received, money=True), fx_to_currency=target)


def balance(entries, as_of_date, policy=POLICY, *, multicurrency=False):
    """Return exact book balances, never marks/NAV or invented prices."""
    if policy == "legacy-eur-v1":
        value = legacy_balance(entries, as_of_date)
        return multi_from_eur(value) if multicurrency else value
    if policy != POLICY:
        raise BookError("unsupported_accounting_policy", "Política contable no soportada.")
    currencies = {'EUR'} | {e['event'].get('currency', 'EUR') for e in entries if e['date'] <= as_of_date}
    currencies |= {e['event']['fx_to_currency'] for e in entries if e['date'] <= as_of_date and e['event']['kind'] == 'fx_exchange'}
    if not currencies <= {'EUR', 'USD'} or (not multicurrency and currencies != {'EUR'}):
        raise BookError('unsupported_currency', 'Este corte requiere la API multidivisa /api/v2; no se convierte ni omite USD.')
    amounts = {c: [ZERO, ZERO, ZERO] for c in currencies}
    positions, sequences = {}, set()
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        for item in sorted(entries, key=lambda e: (e["date"], e["day_sequence"])):
            event = item["event"]
            key = item["date"], item["day_sequence"]
            if key in sequences:
                raise BookError("event_order_ambiguous", "Dos movimientos efectivos ocupan la misma fecha y secuencia.", event.get("source_row"), "day_sequence")
            sequences.add(key)
            if item["date"] > as_of_date:
                continue
            gross, fee = Decimal(event["gross_amount"] or "0"), Decimal(event["fee_amount"] or "0")
            kind, ident = event["kind"], item["listing_id"]
            currency = event['currency']
            cash, contributions, realized = amounts[currency]
            if kind == "deposit":
                cash += gross - fee
                contributions += gross
            elif kind == "withdrawal":
                cash -= gross + fee
                contributions -= gross
            elif kind == "fee":
                cash -= gross
            elif kind == "dividend_payment":
                cash += gross - fee - Decimal(event["tax_amount"])
            elif kind == "split":
                from .corporate import split_quantity
                position = positions.setdefault(ident, [ZERO, ZERO, currency])
                if position[2] != currency:
                    raise BookError('currency_mismatch', 'La posición cambia de moneda.')
                if position[0] <= 0:
                    raise BookError("corporate_position_empty", "El split requiere una posición anterior positiva.")
                position[0] = split_quantity(position[0], event["ratio_numerator"], event["ratio_denominator"], event["fraction_evidence"])
            elif kind in {"buy", "sell"}:
                quantity = Decimal(event["quantity"])
                position = positions.setdefault(ident, [ZERO, ZERO, currency])
                if position[2] != currency:
                    raise BookError('currency_mismatch', 'La posición cambia de moneda.')
                if kind == "buy":
                    cash -= gross + fee
                    position[0] += quantity
                    position[1] += gross + fee
                else:
                    if quantity > position[0]:
                        raise BookError("short_position", "La venta excede la posición disponible.", event.get("source_row"), "quantity")
                    assigned = position[1] if quantity == position[0] else (position[1] * quantity / position[0]).quantize(SCALE)
                    position[0] -= quantity
                    position[1] -= assigned
                    cash += gross - fee
                    realized += gross - fee - assigned
                bounded(position[0], "quantity")
                bounded(position[1], "cost_basis")
            elif kind == 'fx_exchange':
                cash -= gross
                amounts[event['fx_to_currency']][0] += Decimal(event['fx_to_amount'])
                if event['fee_currency'] == currency:
                    cash -= fee
                else:
                    amounts[event['fee_currency']][0] -= fee
            else:
                raise BookError("unsupported_kind", "Movimiento nativo no soportado.")
            amounts[currency] = [cash, contributions, realized]
            for code, values in amounts.items():
                if values[0] < 0:
                    raise BookError('insufficient_cash', f'Efectivo insuficiente en {code} después del movimiento.', event.get('source_row'), 'gross_amount')
                for name, value in zip(('cash', 'net_contributions', 'realized_pnl'), values):
                    bounded(value, name, event.get('source_row'))
    result = dict(as_of_date=as_of_date, balances=[dict(currency=c, cash=decimal_text(v[0], money=True),
                  net_contributions=decimal_text(v[1], money=True), realized_pnl=decimal_text(v[2])) for c, v in sorted(amounts.items())],
                  positions=[dict(listing_id=k, currency=v[2], quantity=decimal_text(v[0]), cost_basis=decimal_text(v[1]))
                             for k, v in sorted(positions.items()) if v[0]], warnings=[])
    return result if multicurrency else eur_from_multi(result)


def multi_from_eur(value):
    if 'balances' in value:
        return value
    return dict(as_of_date=value['as_of_date'], balances=[{k: value[k] for k in ('currency', 'cash', 'net_contributions', 'realized_pnl')}],
                positions=[{**p, 'currency': 'EUR'} for p in value['positions']], warnings=value['warnings'])


def eur_from_multi(value):
    if 'balances' not in value:
        return value
    if any(b['currency'] != 'EUR' for b in value['balances']) or any(p['currency'] != 'EUR' for p in value['positions']):
        raise BookError('unsupported_currency', 'Consulta este documento/corte con la API multidivisa /api/v2.')
    return dict(as_of_date=value['as_of_date'], **value['balances'][0],
                positions=[{k: v for k, v in p.items() if k != 'currency'} for p in value['positions']], warnings=value['warnings'])


def legacy_balance(entries, as_of_date):
    from .analytics import _normalize_events, apply_legacy_event
    state = dict(cash=ZERO, contributions=ZERO, quantities={}, costs={})
    events = [{**item["event"], "symbol": item["listing_id"].upper() if item["listing_id"] else None}
              for item in entries if item["date"] <= as_of_date]
    for event in _normalize_events(events):
        apply_legacy_event(state, event)
    warnings = ["Libro heredado: conserva precisión y convenciones originales."]
    with localcontext() as context:
        context.prec = 64
        if state["cash"] != state["cash"].quantize(CENT):
            warnings.append("El efectivo heredado contiene fracciones de céntimo; no se redondea para conciliar.")
    return dict(as_of_date=as_of_date, currency="EUR", cash=decimal_text(state["cash"]),
                net_contributions=decimal_text(state["contributions"]), realized_pnl=None,
                positions=[dict(listing_id=k.lower(), quantity=decimal_text(v), cost_basis=decimal_text(state["costs"][k]))
                           for k, v in sorted(state["quantities"].items()) if v], warnings=warnings)


def parse_statement(content, mapping, as_of_date, *, multicurrency=False, catalog=None):
    end = cutoff(as_of_date)
    values = {}
    for line, raw in rows(content, STATEMENT_COLUMNS):
        if raw["as_of_date"] != end:
            raise BookError("cut_mismatch", "Todas las filas deben tener la fecha de corte declarada.", line, "as_of_date")
        currency = raw['currency']
        if currency not in (('EUR', 'USD') if multicurrency else ('EUR',)):
            raise BookError("unsupported_currency", "D4 concilia exclusivamente EUR.", line, "currency")
        if raw["record_type"] == "cash":
            if raw["listing_ref"] or raw["quantity"]:
                raise BookError("incompatible_field", "Efectivo no lleva cotización ni cantidad.", line)
            key, value = ("cash", currency if multicurrency else None), number(raw["amount"], "amount", 2, line)
        elif raw["record_type"] == "position":
            if raw["amount"]:
                raise BookError("incompatible_field", "Una posición no lleva importe de efectivo.", line, "amount")
            key = "position", listing(raw["listing_ref"], mapping, line)
            if catalog:
                validate_currencies([(line, dict(listing_id=key[1], currency=currency))], catalog)
            value = number(raw["quantity"], "quantity", 12, line)
        else:
            raise BookError("invalid_record_type", "Se requiere cash o position.", line, "record_type")
        if key in values:
            raise BookError("duplicate_conflict", "Clave duplicada en el extracto.", line)
        values[key] = value
    if ("cash", 'EUR' if multicurrency else None) not in values:
        raise BookError("incomplete_statement", "Falta la fila de efectivo EUR del extracto completo.")
    return values


def reconcile(book, reference, catalog=None):
    if 'balances' in book:
        return reconcile_multi(book, reference, catalog)
    actual = {("cash", None): Decimal(book["cash"])}
    actual.update({("position", p["listing_id"]): Decimal(p["quantity"]) for p in book["positions"]})
    differences = []
    with localcontext() as context:
        context.prec, context.rounding = 64, ROUND_HALF_EVEN
        for kind, ident in sorted(actual.keys() | reference.keys(), key=lambda k: (k[0], k[1] or "")):
            expected, recorded = reference.get((kind, ident), ZERO), actual.get((kind, ident), ZERO)
            delta = bounded(expected - recorded, "difference")
            differences.append(dict(record_type=kind, listing_id=ident, currency="EUR",
                book=decimal_text(recorded), reference=decimal_text(expected),
                difference=decimal_text(delta), matched=delta == 0))
    return differences


def reconcile_multi(book, reference, catalog):
    currencies = {p['id']: p['currency'] for p in (catalog or {}).get('listings', [])}
    currencies.update({p['listing_id']: p['currency'] for p in book['positions']})
    for b in book['balances']:
        if ('cash', b['currency']) not in reference:
            raise BookError('incomplete_statement', f"Falta efectivo {b['currency']} en el extracto completo.")
    actual = {('cash', b['currency']): Decimal(b['cash']) for b in book['balances']}
    actual.update({('position', p['listing_id']): Decimal(p['quantity']) for p in book['positions']})
    rows = []
    with localcontext() as ctx:
        ctx.prec, ctx.rounding = 64, ROUND_HALF_EVEN
        for key in sorted(actual.keys() | reference.keys()):
            kind, ident = key
            recorded, expected = actual.get(key, ZERO), reference.get(key, ZERO)
            delta = bounded(expected - recorded, 'difference')
            rows.append(dict(record_type=kind, listing_id=ident if kind == 'position' else None,
                currency=ident if kind == 'cash' else currencies.get(ident), book=decimal_text(recorded),
                reference=decimal_text(expected), difference=decimal_text(delta), matched=delta == 0))
    return rows

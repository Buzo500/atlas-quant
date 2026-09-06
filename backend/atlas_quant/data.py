"""Validated CSV ingestion and explicitly synthetic demonstration data.

CSV numbers use a decimal point, without thousands separators. Separators may be
commas, semicolons or tabs; UTF-8 BOM is accepted. Dates are ISO YYYY-MM-DD.
ATLAS v0.1 accepts EUR only: foreign-currency values require an FX-aware ledger,
which this module deliberately does not approximate.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


MAX_CSV_ROWS = 1_000_000
SCHEMA_VERSION = "atlas.quant.data.v1"
_PRICE_REQUIRED = {"date", "symbol", "open", "high", "low", "close", "volume"}
_PRICE_ALLOWED = _PRICE_REQUIRED | {"currency"}
_LEDGER_ALLOWED = {
    "id", "date", "kind", "symbol", "quantity", "price", "amount", "fee", "currency"
}
_KINDS = {"deposit", "withdrawal", "buy", "sell", "dividend", "fee", "split"}
_DECIMAL = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)\Z", re.ASCII)
_SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9_.:\-]{0,39}\Z", re.ASCII)


class DataValidationError(ValueError):
    """An input failed the data contract; no partial import should be committed."""


def _rows(text: str, required: set[str], allowed: set[str]):
    if not isinstance(text, str):
        raise DataValidationError("Se esperaba texto Unicode decodificado como UTF-8.")
    try:
        text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise DataValidationError("El archivo no contiene texto UTF-8 válido.") from exc
    text = text.lstrip("\ufeff")
    if not text.strip():
        raise DataValidationError("El CSV está vacío.")
    # Select from the schema's header, never from values containing commas.
    header = text.splitlines()[0]
    delimiter = max((",", ";", "\t"), key=header.count)
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        original = reader.fieldnames
        if not original:
            raise DataValidationError("El CSV debe incluir una cabecera.")
        fields = [column.strip().lower() for column in original]
        if len(set(fields)) != len(fields) or "" in fields:
            raise DataValidationError("Hay columnas vacías o duplicadas en la cabecera.")
        missing = required - set(fields)
        unknown = set(fields) - allowed
        if missing:
            raise DataValidationError("Faltan columnas obligatorias: " + ", ".join(sorted(missing)) + ".")
        if unknown:
            raise DataValidationError("Columnas no reconocidas: " + ", ".join(sorted(unknown)) + ".")
        reader.fieldnames = fields
        count = 0
        for raw in reader:
            line = reader.line_num
            if None in raw or any(value is None for value in raw.values()):
                raise DataValidationError(f"Fila {line}: número de columnas incorrecto.")
            row = {key: value.strip() for key, value in raw.items()}
            if not any(row.values()):
                continue
            count += 1
            if count > MAX_CSV_ROWS:
                raise DataValidationError(f"El CSV supera el límite de {MAX_CSV_ROWS:,} filas.")
            yield line, row
    except csv.Error as exc:
        raise DataValidationError(f"CSV mal formado: {exc}.") from exc


def _iso_date(value: str, line: int) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value, flags=re.ASCII):
        raise DataValidationError(f"Fila {line}: date debe usar YYYY-MM-DD.")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise DataValidationError(f"Fila {line}: fecha inválida: {value}.") from exc


def _symbol(value: str, line: int, *, required: bool = True) -> str:
    value = value.upper()
    if not value and not required:
        return ""
    if not _SYMBOL.fullmatch(value):
        raise DataValidationError(f"Fila {line}: symbol inválido; usa un identificador de hasta 40 caracteres.")
    return value


def _currency(value: str, line: int) -> str:
    value = (value or "EUR").upper()
    if value != "EUR":
        raise DataValidationError(
            f"Fila {line}: moneda {value!r} no soportada. ATLAS admite EUR; hace falta conversión FX explícita."
        )
    return value


def _decimal(value: str, field: str, line: int, *, default: str | None = None) -> Decimal:
    if value == "" and default is not None:
        value = default
    if len(value) > 64 or not _DECIMAL.fullmatch(value):
        raise DataValidationError(
            f"Fila {line}: {field} debe ser un número finito con punto decimal, sin separadores de miles."
        )
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise DataValidationError(f"Fila {line}: {field} no es un decimal válido.") from exc
    if not result.is_finite() or not math.isfinite(float(result)):
        raise DataValidationError(f"Fila {line}: {field} debe ser finito.")
    return result


def _canonical_decimal(value: Decimal) -> str:
    if not value:
        return "0"
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def parse_prices_csv(text: str) -> list[dict[str, Any]]:
    """Parse complete daily OHLCV bars, sorted by date and symbol.

    Required columns: date,symbol,open,high,low,close,volume. The optional
    currency column defaults to EUR; any other currency is rejected. All
    prices must be positive and finite; volume is nonnegative. No price or
    volume is imputed, and duplicate (date, symbol) rows fail the whole import.
    A dataset needs at least two bars, but may contain gaps or sparse symbols;
    strategy suitability is a separate validation step.
    """
    bars: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for line, row in _rows(text, _PRICE_REQUIRED, _PRICE_ALLOWED):
        day = _iso_date(row["date"], line)
        symbol = _symbol(row["symbol"], line)
        currency = _currency(row.get("currency", ""), line)
        key = (day, symbol)
        if key in seen:
            raise DataValidationError(f"Fila {line}: barra duplicada para {symbol} el {day}.")
        values = {field: _decimal(row[field], field, line) for field in ("open", "high", "low", "close", "volume")}
        for field in ("open", "high", "low", "close"):
            if values[field] <= 0:
                raise DataValidationError(f"Fila {line}: {field} debe ser mayor que cero.")
        if values["volume"] < 0:
            raise DataValidationError(f"Fila {line}: volume no puede ser negativo.")
        if not (values["low"] <= min(values["open"], values["close"]) <= max(values["open"], values["close"]) <= values["high"]):
            raise DataValidationError(f"Fila {line}: OHLC inconsistente; low <= open/close <= high.")
        bars.append({"date": day, "symbol": symbol, **{field: float(value) for field, value in values.items()}, "currency": currency})
        seen.add(key)
    if len(bars) < 2:
        raise DataValidationError("Se necesitan al menos dos barras de precios.")
    return sorted(bars, key=lambda bar: (bar["date"], bar["symbol"]))


def parse_ledger_csv(text: str) -> list[dict[str, str]]:
    """Parse cash/position events, preserving decimal precision in strings.

    Required columns are date and kind. Every row must provide the fields
    relevant to its kind: deposit/withdrawal/dividend/fee require positive
    amount; buy/sell require positive quantity and price; split requires a
    positive quantity representing new shares / old shares. Trades' amount
    is gross quantity * price and is derived if omitted. fee is a separate
    nonnegative trade cost. Irrelevant numeric fields default to zero and must
    be zero. Dividends are the cash received; record withholding separately as
    kind=fee if importing gross dividends. This is a cash ledger, not a tax
    report. Corporate actions and cash events are never inferred from prices.

    IDs are optional. If absent, a deterministic SHA256 of the normalized row
    is used. Identical rows with the same ID are deduplicated; ID collisions
    with different contents fail. Give distinct external IDs for separate
    otherwise identical events (for example two deposits on the same day).
    Events are sorted by date, preserving input order within a day.
    """
    events: list[dict[str, str]] = []
    seen: dict[str, dict[str, str]] = {}
    for line, row in _rows(text, {"date", "kind"}, _LEDGER_ALLOWED):
        day = _iso_date(row["date"], line)
        kind = row["kind"].lower()
        if kind not in _KINDS:
            raise DataValidationError(f"Fila {line}: kind desconocido: {kind!r}.")
        symbol = _symbol(row.get("symbol", ""), line, required=kind in {"buy", "sell", "dividend", "split"})
        currency = _currency(row.get("currency", ""), line)
        numbers = {field: _decimal(row.get(field, ""), field, line, default="0") for field in ("quantity", "price", "amount", "fee")}
        if any(value < 0 for value in numbers.values()):
            raise DataValidationError(f"Fila {line}: usa importes no negativos; kind determina el sentido del flujo.")
        if kind in {"buy", "sell"}:
            if numbers["quantity"] <= 0 or numbers["price"] <= 0:
                raise DataValidationError(f"Fila {line}: buy/sell requieren quantity y price positivos.")
            with localcontext() as context:
                context.prec = 128
                gross = numbers["quantity"] * numbers["price"]
            if row.get("amount", "") and numbers["amount"] != gross:
                raise DataValidationError(f"Fila {line}: amount debe coincidir exactamente con quantity * price (bruto).")
            numbers["amount"] = gross
        elif kind == "split":
            if numbers["quantity"] <= 0 or any(numbers[field] for field in ("price", "amount", "fee")):
                raise DataValidationError(f"Fila {line}: split requiere quantity como factor positivo y price/amount/fee iguales a cero.")
        else:
            if numbers["amount"] <= 0:
                raise DataValidationError(f"Fila {line}: {kind} requiere amount positivo.")
            if any(numbers[field] for field in ("quantity", "price", "fee")):
                raise DataValidationError(f"Fila {line}: {kind} usa amount; quantity/price/fee deben estar vacíos o ser cero.")
            if kind in {"deposit", "withdrawal"} and symbol:
                raise DataValidationError(f"Fila {line}: {kind} es un movimiento de efectivo sin symbol.")
        payload = {"date": day, "kind": kind, "symbol": symbol, **{field: _canonical_decimal(value) for field, value in numbers.items()}, "currency": currency}
        event_id = row.get("id", "")
        if event_id and (len(event_id) > 128 or any(ord(char) < 32 or ord(char) == 127 for char in event_id)):
            raise DataValidationError(f"Fila {line}: id debe tener hasta 128 caracteres y no contener caracteres de control.")
        if not event_id:
            event_id = "csv_" + hashlib.sha256(_canonical_json(payload)).hexdigest()
        if event_id in seen:
            if seen[event_id] != payload:
                raise DataValidationError(f"Fila {line}: id {event_id!r} repetido con contenido diferente.")
            continue
        seen[event_id] = payload
        events.append({"id": event_id, **payload})
    if not events:
        raise DataValidationError("El libro mayor debe contener al menos un movimiento.")
    return sorted(events, key=lambda event: event["date"])


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def build_provenance_manifest(bars: list[dict[str, Any]], name: str, source_kind: str, source: str) -> dict[str, Any]:
    """Describe and hash a validated price dataset independently of import time.

    The SHA256 covers canonical, date/symbol-sorted bars with normalized numeric
    types and schema_version. It identifies the imported snapshot; it does not
    verify that the supplier is accurate, prices are adjusted or an exchange was
    open. generated_at is manifest creation time, never a quote timestamp.
    """
    if not bars:
        raise DataValidationError("No se puede generar procedencia para un dataset vacío.")
    if not name.strip() or not source.strip() or not source_kind.strip():
        raise DataValidationError("La procedencia necesita name, source_kind y source.")
    canonical = [
        {"date": bar["date"], "symbol": bar["symbol"], "currency": bar.get("currency", "EUR"),
         **{field: float(bar[field]) for field in ("open", "high", "low", "close", "volume")}}
        for bar in sorted(bars, key=lambda bar: (bar["date"], bar["symbol"]))
    ]
    symbols = sorted({bar["symbol"] for bar in canonical})
    counts = dict(sorted(Counter(bar["symbol"] for bar in canonical).items()))
    return {
        "schema_version": SCHEMA_VERSION,
        "hash_algorithm": "sha256",
        "hash_version": 1,
        "sha256": hashlib.sha256(_canonical_json({"schema_version": SCHEMA_VERSION, "bars": canonical})).hexdigest(),
        "name": name,
        "source_kind": source_kind,
        "source": source,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date_min": canonical[0]["date"],
        "date_max": canonical[-1]["date"],
        "symbols": symbols,
        "row_count": len(canonical),
        "counts_by_symbol": counts,
        "currencies": sorted({bar["currency"] for bar in canonical}),
        "synthetic": source_kind == "synthetic",
        "price_basis": "unspecified",
        "calendar": "provided_rows_only",
        "warnings": [
            "Datos sintéticos: no son cotizaciones ni evidencia de rentabilidad real."
            if source_kind == "synthetic" else
            "La importación no verifica ajuste por dividendos/splits ni cobertura de activos excluidos."
        ],
    }


def price_csv_template() -> str:
    """An importable, visibly fictional two-bar OHLCV example."""
    return "date,symbol,open,high,low,close,volume,currency\n2026-01-05,DEMO_WORLD,100,102,99,101,100000,EUR\n2026-01-06,DEMO_WORLD,101,103,100,102,120000,EUR\n"


def ledger_csv_template() -> str:
    """An importable, visibly fictional deposit/purchase example."""
    return "id,date,kind,symbol,quantity,price,amount,fee,currency\nexample-deposit,2026-01-05,deposit,,,,10000,,EUR\nexample-buy,2026-01-06,buy,DEMO_WORLD,10,101,,1,EUR\n"


def demo_dataset() -> dict[str, Any]:
    """Return a reproducible synthetic market and ledger for local exploration.

    There are 1,100 Monday-Friday dates ending on the current UTC weekday (or
    Friday during weekends). Weekdays are not an exchange holiday calendar.
    A fixed PRNG seed preserves the path while dates advance with today.
    No live quotes, real securities or simulated operating history are implied.
    """
    final_day = datetime.now(timezone.utc).date()
    while final_day.weekday() > 4:
        final_day -= timedelta(days=1)
    days: list[date] = []
    day = final_day
    while len(days) < 1100:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    days.reverse()
    generator = random.Random(20260905)
    specs = {"DEMO_WORLD": (100.0, 0.00022, 0.010), "DEMO_EURO": (80.0, 0.00013, 0.012), "DEMO_BOND": (50.0, 0.00007, 0.0028)}
    levels = {symbol: values[0] for symbol, values in specs.items()}
    bars: list[dict[str, Any]] = []
    for index, day in enumerate(days):
        common_shock = generator.gauss(0, 1)
        # Several explicit synthetic market regimes avoid a uniformly rising demo.
        regime = -0.0014 if 280 <= index < 355 or 765 <= index < 825 else 0.0
        for symbol, (_, drift, volatility) in specs.items():
            previous = levels[symbol]
            exposure = 0.72 if symbol != "DEMO_BOND" else -0.12
            shock = exposure * common_shock + math.sqrt(1 - exposure ** 2) * generator.gauss(0, 1)
            gap = generator.gauss(0, volatility * 0.16)
            opening = previous * math.exp(gap)
            daily_return = drift + volatility * shock + (regime if symbol != "DEMO_BOND" else 0)
            close = previous * math.exp(daily_return)
            excursion = abs(generator.gauss(0, volatility * 0.45)) + 0.0003
            high = max(opening, close) * (1 + excursion)
            low = min(opening, close) * (1 - min(excursion, 0.5))
            levels[symbol] = close
            bars.append({"date": day.isoformat(), "symbol": symbol, "open": round(opening, 6), "high": round(high, 6), "low": round(low, 6), "close": round(close, 6), "volume": float(generator.randint(80000, 2000000)), "currency": "EUR"})
    bars.sort(key=lambda bar: (bar["date"], bar["symbol"]))
    events_csv = io.StringIO(newline="")
    writer = csv.writer(events_csv)
    writer.writerow(["id", "date", "kind", "symbol", "quantity", "price", "amount", "fee", "currency"])
    writer.writerow(["demo-deposit", days[0].isoformat(), "deposit", "", "", "", "25000", "", "EUR"])
    for bar, quantity in zip(bars[:3], (100, 80, 60)):
        writer.writerow(["demo-buy-" + bar["symbol"], bar["date"], "buy", bar["symbol"], quantity, bar["close"], "", "1", "EUR"])
    writer.writerow(["demo-deposit-2", days[700].isoformat(), "deposit", "", "", "", "2500", "", "EUR"])
    writer.writerow(["demo-custody-fee", days[900].isoformat(), "fee", "", "", "", "3", "", "EUR"])
    name = "Cartera de demostración · datos sintéticos"
    source = "Generador sintético ATLAS v0.1; semilla 20260905; activos ficticios."
    metadata = build_provenance_manifest(bars, name, "synthetic", source)
    metadata.update({"seed": 20260905, "business_days": len(days), "calendar": "weekdays_without_exchange_holidays", "price_basis": "synthetic_unadjusted_no_corporate_actions", "adjusted": False, "is_live": False, "description": "Tres activos ficticios denominados en EUR. Los días históricos son escenarios, no días de operativa registrada."})
    return {"name": name, "source_kind": "synthetic", "source": source, "bars": bars, "events": parse_ledger_csv(events_csv.getvalue()), "metadata": metadata}

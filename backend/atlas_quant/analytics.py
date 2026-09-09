"""Deterministic EUR ledger accounting; no market data are fabricated.

Ledger amounts use Decimal throughout. Public results contain JSON numbers.
Daily TWR assumes external cash flows occur at the close; the first funded
day establishes its base and therefore has no measurable daily TWR.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

ZERO = Decimal("0")


def decimal_value(value: Any, name: str, *, positive: bool = False) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name}: se requiere un número finito.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name}: número no válido.") from exc
    if not number.is_finite() or number < ZERO or (positive and number == ZERO):
        raise ValueError(f"{name}: debe ser {'positivo' if positive else 'no negativo'} y finito.")
    # Keep arithmetic and float serialization within a practical, explicit bound.
    if number > Decimal("1e18"):
        raise ValueError(f"{name}: supera el límite admitido de 1e18.")
    return number


def iso_date(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.") from exc
    if parsed.isoformat() != value:
        raise ValueError("La fecha debe tener formato YYYY-MM-DD.")
    return value


def symbol_value(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
        raise ValueError("Se requiere un símbolo de entre 1 y 64 caracteres.")
    return value.strip().upper()


def normalize_bars(bars: list[dict]) -> list[dict]:
    if not isinstance(bars, list):
        raise ValueError("Las barras deben ser una lista.")
    normalized = []
    seen: set[tuple[str, str]] = set()
    for raw in bars:
        if not isinstance(raw, dict):
            raise ValueError("Cada barra debe ser un objeto.")
        if raw.get("currency", "EUR") != "EUR":
            raise ValueError("La versión inicial admite exclusivamente EUR; falta conversión FX verificada.")
        day = iso_date(raw.get("date"))
        symbol = symbol_value(raw.get("symbol"))
        key = day, symbol
        if key in seen:
            raise ValueError(f"Barra duplicada: {symbol} {day}.")
        seen.add(key)
        prices = {field: decimal_value(raw.get(field), field, positive=True)
                  for field in ("open", "high", "low", "close")}
        if (prices["high"] < max(prices.values())
                or prices["low"] > min(prices.values())):
            raise ValueError(f"OHLC incoherente: {symbol} {day}.")
        volume = decimal_value(raw.get("volume", 0), "volume")
        normalized.append({"date": day, "symbol": symbol, **prices,
                           "volume": volume, "currency": "EUR"})
    return sorted(normalized, key=lambda item: (item["date"], item["symbol"]))


def _normalize_events(events: list[dict]) -> list[dict]:
    if not isinstance(events, list):
        raise ValueError("Los movimientos deben ser una lista.")
    normalized = []
    seen = set()
    kinds = {"deposit", "withdrawal", "buy", "sell", "dividend", "fee", "split"}
    for raw in events:
        if not isinstance(raw, dict):
            raise ValueError("Cada movimiento debe ser un objeto.")
        identifier = raw.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("Cada movimiento necesita un id no vacío.")
        if identifier in seen:
            raise ValueError(f"Movimiento duplicado: {identifier}.")
        seen.add(identifier)
        if raw.get("currency", "EUR") != "EUR":
            raise ValueError("Los movimientos de esta versión deben estar en EUR.")
        kind = raw.get("kind")
        if kind not in kinds:
            raise ValueError(f"Tipo de movimiento no admitido: {kind}.")
        fields = {field: decimal_value(raw.get(field, "0"), field)
                  for field in ("quantity", "price", "amount", "fee")}
        symbol = symbol_value(raw.get("symbol")) if raw.get("symbol") else None
        if kind in {"buy", "sell", "split"} and symbol is None:
            raise ValueError(f"{kind}: se requiere símbolo.")
        if kind in {"buy", "sell"}:
            if fields["quantity"] == ZERO or fields["price"] == ZERO:
                raise ValueError("Una compraventa requiere cantidad y precio positivos.")
            if fields["amount"] not in (ZERO, fields["quantity"] * fields["price"]):
                raise ValueError("amount de una compraventa debe ser cero o cantidad × precio, sin comisión.")
        elif kind == "split":
            if fields["quantity"] == ZERO:
                raise ValueError("split.quantity debe ser el ratio positivo de acciones nuevas/antiguas.")
            if any(fields[field] != ZERO for field in ("price", "amount", "fee")):
                raise ValueError("Un split solo admite quantity como ratio; price, amount y fee deben ser cero.")
        else:
            if fields["amount"] == ZERO:
                raise ValueError(f"{kind}: amount debe ser positivo.")
            if fields["quantity"] != ZERO or fields["price"] != ZERO:
                raise ValueError(f"{kind}: quantity y price deben ser cero.")
            if kind == "fee" and fields["fee"] != ZERO:
                raise ValueError("Un movimiento fee se registra en amount; fee debe ser cero para evitar duplicarlo.")
        normalized.append({"id": identifier, "date": iso_date(raw.get("date")),
                           "kind": kind, "symbol": symbol, **fields})
    # The caller's order is preserved inside each date: fills and splits are ordered events.
    return sorted(normalized, key=lambda item: item["date"])


def apply_legacy_event(state: dict, event: dict) -> Decimal:
    """Shared legacy economic transition; no prices or change of conventions."""
    cash, contributions = state["cash"], state["contributions"]
    quantities, costs = state["quantities"], state["costs"]
    day, flow = event["date"], ZERO
    kind, symbol = event["kind"], event["symbol"]
    amount, fee = event["amount"], event["fee"]
    quantity, price = event["quantity"], event["price"]
    if kind == "deposit":
        cash += amount - fee
        contributions += amount
        flow += amount
    elif kind == "withdrawal":
        cash -= amount + fee
        contributions -= amount
        flow -= amount
    elif kind == "buy":
        gross_cost = quantity * price + fee
        cash -= gross_cost
        quantities[symbol] = quantities.get(symbol, ZERO) + quantity
        costs[symbol] = costs.get(symbol, ZERO) + gross_cost
    elif kind == "sell":
        held = quantities.get(symbol, ZERO)
        if quantity > held:
            raise ValueError(f"Venta de {symbol} excede la posición; no se admiten cortos.")
        costs[symbol] -= costs[symbol] * quantity / held
        quantities[symbol] -= quantity
        cash += quantity * price - fee
    elif kind == "dividend":
        cash += amount - fee
    elif kind == "fee":
        cash -= amount
    elif kind == "split":
        if quantities.get(symbol, ZERO) == ZERO:
            raise ValueError(f"Split de {symbol} sin una posición abierta.")
        quantities[symbol] *= quantity
    if cash < ZERO:
        raise ValueError(f"Efectivo insuficiente después del movimiento {event['id']} ({day}).")
    state["cash"], state["contributions"] = cash, contributions
    return flow


def portfolio_snapshot(events: list[dict], bars: list[dict]) -> dict:
    ledger = _normalize_events(events)
    market = normalize_bars(bars)
    warnings = ["TWR diario aproximado: aportaciones y retiradas al cierre; el primer día financiado establece la base."]
    cash = ZERO
    contributions = ZERO
    previous_nav = ZERO
    twr_index = Decimal("1")
    quantities: dict[str, Decimal] = {}
    costs: dict[str, Decimal] = {}
    prices: dict[str, Decimal] = {}
    price_dates: dict[str, str] = {}
    curves = []
    event_days: dict[str, list[dict]] = {}
    market_days: dict[str, list[dict]] = {}
    for event in ledger:
        event_days.setdefault(event["date"], []).append(event)
    for bar in market:
        market_days.setdefault(bar["date"], []).append(bar)
    all_dates = sorted(set(event_days) | set(market_days))
    if not ledger:
        all_dates = []
    elif all_dates:
        # Older bars are still made available as as-of marks, but do not pad the performance period.
        start = ledger[0]["date"]
        for bar in market:
            if bar["date"] < start:
                prices[bar["symbol"]] = bar["close"]
                price_dates[bar["symbol"]] = bar["date"]
        all_dates = [day for day in all_dates if day >= start]
    stale_symbols: set[str] = set()
    for day in all_dates:
        flow = ZERO
        for event in event_days.get(day, []):
            state = dict(cash=cash, contributions=contributions, quantities=quantities, costs=costs)
            flow += apply_legacy_event(state, event)
            cash, contributions = state["cash"], state["contributions"]
            if event["kind"] == "split":
                # The previous mark is on the old share basis.
                prices.pop(event["symbol"], None)
                price_dates.pop(event["symbol"], None)
        for bar in market_days.get(day, []):
            prices[bar["symbol"]] = bar["close"]
            price_dates[bar["symbol"]] = day
        nav = cash
        for symbol, quantity in quantities.items():
            if quantity:
                if symbol not in prices:
                    raise ValueError(f"No hay cierre disponible a fecha {day} para valorar {symbol}.")
                if price_dates[symbol] != day:
                    stale_symbols.add(symbol)
                nav += quantity * prices[symbol]
        if previous_nav > ZERO:
            factor = (nav - flow) / previous_nav
            if factor < ZERO:
                raise ValueError("TWR no interpretable: patrimonio ajustado por flujos negativo.")
            twr_index *= factor
        elif nav > ZERO and curves:
            warnings.append(f"{day}: TWR reiniciado tras patrimonio cero; no es una serie enlazada comparable.")
            twr_index = Decimal("1")
        curves.append({"date": day, "nav": float(nav), "twr_index": float(twr_index)})
        previous_nav = nav
    if stale_symbols:
        warnings.append("Se utilizaron últimos cierres conocidos en fechas sin barra: "
                        + ", ".join(sorted(stale_symbols)) + ". Revise la antigüedad del dato.")
    nav = previous_nav
    positions = []
    for symbol in sorted(quantities):
        quantity = quantities[symbol]
        if not quantity:
            continue
        value = quantity * prices[symbol]
        positions.append({"symbol": symbol, "quantity": float(quantity),
                          "price": float(prices[symbol]), "price_date": price_dates[symbol],
                          "market_value": float(value), "weight": float(value / nav) if nav else 0.0,
                          "cost_basis": float(costs[symbol]), "unrealized_pnl": float(value - costs[symbol])})
    return {"nav": float(nav), "cash": float(cash), "net_contributions": float(contributions),
            "pnl": float(nav - contributions), "twr": float(twr_index - 1),
            "positions": positions, "curve": curves, "warnings": list(dict.fromkeys(warnings))}

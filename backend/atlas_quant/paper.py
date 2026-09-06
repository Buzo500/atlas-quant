"""Persistent paper execution with close signals and strictly later open fills.

These functions have no broker, network or persistence access. The caller must
atomically store the returned copy; exceptions leave its original untouched.
Imported bars are scenarios, not verified live quotes or proof of market fills.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from typing import Any

from .analytics import ZERO, decimal_value, iso_date, normalize_bars
from .backtest import normalize_strategy


_WARNINGS = [
    "Paper trading local: las órdenes y ejecuciones son simuladas; no se contacta con ningún bróker.",
    "Señal al cierre y ejecución en una apertura observada estrictamente posterior; los datos importados no prueban una ejecución real.",
    "EUR, acciones enteras, sin cortos ni apalancamiento. Comisiones y deslizamiento son supuestos; no se modelan spread, impacto ni ejecuciones parciales.",
    "El límite de peso se comprueba al comprar; variaciones posteriores del mercado pueden superarlo sin provocar rebalanceo automático.",
]


def new_account(initial_cash=10000, *, started_at_date: str | None = None) -> dict[str, Any]:
    """Create a cash-only paper account with an exclusive processing cutoff.

    Default cutoff is today in UTC, so old imported history cannot masquerade
    as newly observed paper performance. An explicit older cutoff is supported
    for testing/replay. A cutoff bar may warm indicators but never submit orders.
    """
    initial = decimal_value(initial_cash, "initial_cash", positive=True)
    cutoff = iso_date(started_at_date) if started_at_date is not None else datetime.now(timezone.utc).date().isoformat()
    return {
        "mode": "paper", "currency": "EUR", "initial_cash": float(initial),
        "cash": float(initial), "positions": {}, "orders": [], "fills": [],
        "last_processed_date": cutoff, "started_at_date": cutoff,
        "strategy": None, "equity": float(initial), "equity_curve": [],
        "last_price": None, "last_price_date": None, "last_prices": {},
        "observed_bars": [], "warnings": list(_WARNINGS), "enabled": False,
    }


def _serial_bar(bar: dict) -> dict:
    return {key: float(value) if isinstance(value, Decimal) else value for key, value in bar.items()}


def _desired_position(closes: list[Decimal], index: int, rule: dict) -> bool:
    if rule["kind"] == "buy_hold":
        return True
    if rule["kind"] == "sma_cross":
        slow, fast = rule["slow_window"], rule["fast_window"]
        if index + 1 < slow:
            return False
        end = index + 1
        return sum(closes[end - fast:end], ZERO) / fast > sum(closes[end - slow:end], ZERO) / slow
    lookback = rule["lookback"]
    return index >= lookback and closes[index] > closes[index - lookback]


def _whole(value: Decimal) -> Decimal:
    return value.to_integral_value(rounding=ROUND_FLOOR)


def _buy_size(cash: Decimal, price: Decimal, weight: Decimal, commission: Decimal, minimum: Decimal) -> Decimal:
    if cash <= minimum:
        return ZERO
    # Both fee regimes must satisfy cash and post-fee equity weight. Valuing the
    # position at the slipped execution price is conservative relative to open.
    cash_proportional = cash / (price * (1 + commission))
    cash_fixed = (cash - minimum) / price
    weight_proportional = weight * cash / (price * (1 + weight * commission))
    weight_fixed = weight * (cash - minimum) / price
    return max(ZERO, _whole(min(cash_proportional, cash_fixed, weight_proportional, weight_fixed)))


def _validate_account(account: dict, rule: dict) -> tuple[Decimal, Decimal]:
    if not isinstance(account, dict) or account.get("mode") != "paper" or account.get("currency") != "EUR":
        raise ValueError("Se requiere una cuenta paper EUR creada con new_account.")
    iso_date(account.get("started_at_date"))
    iso_date(account.get("last_processed_date"))
    if account["last_processed_date"] < account["started_at_date"]:
        raise ValueError("El marcador de proceso precede al inicio de la cuenta.")
    cash = decimal_value(account.get("cash"), "paper.cash")
    positions = account.get("positions")
    if not isinstance(positions, dict):
        raise ValueError("paper.positions debe ser un objeto.")
    quantity = ZERO
    for symbol, raw in positions.items():
        size = decimal_value(raw, "paper.position")
        if size != _whole(size):
            raise ValueError("Paper v0.1 admite acciones enteras.")
        if symbol != rule["symbol"] and size:
            raise ValueError("La cuenta paper solo puede contener el símbolo de su estrategia congelada.")
        if symbol == rule["symbol"]:
            quantity = size
    pending_count = 0
    for field in ("orders", "fills", "equity_curve", "observed_bars", "warnings"):
        if not isinstance(account.get(field), list):
            raise ValueError(f"paper.{field} debe ser una lista.")
    seen_ids = set()
    for order in account["orders"]:
        if not isinstance(order, dict) or not isinstance(order.get("id"), str) or not order["id"]:
            raise ValueError("La cuenta contiene una orden inválida.")
        if order["id"] in seen_ids:
            raise ValueError("La cuenta contiene IDs de órdenes duplicados.")
        seen_ids.add(order["id"])
        if order.get("status") not in {"pending", "filled", "rejected", "cancelled"}:
            raise ValueError("Estado de orden paper inválido.")
        if order.get("side") not in {"buy", "sell"} or order.get("symbol") != rule["symbol"]:
            raise ValueError("Dirección o símbolo de orden paper inválido.")
        signal_date = iso_date(order.get("signal_date"))
        if not account["started_at_date"] < signal_date <= account["last_processed_date"]:
            raise ValueError("La señal de la orden queda fuera del periodo observado.")
        if order["status"] == "pending":
            pending_count += 1
    if pending_count > 1:
        raise ValueError("La cuenta no puede tener más de una orden pendiente.")
    fill_ids = set()
    for fill in account["fills"]:
        if not isinstance(fill, dict) or fill.get("order_id") not in seen_ids or fill.get("id") in fill_ids:
            raise ValueError("La cuenta contiene una ejecución inválida o duplicada.")
        fill_ids.add(fill.get("id"))
    try:
        json.dumps(account, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("La cuenta debe ser JSON con números finitos.") from exc
    return cash, quantity


def advance_paper(account: dict, bars: list[dict], strategy: dict, *, enabled: bool,
                  max_position_weight: float = 0.25, commission_bps=5,
                  slippage_bps=5, minimum_fee=1.25) -> dict[str, Any]:
    """Advance a copied account once per new observed daily bar.

    Full snapshots and incremental batches are supported; saved history warms
    indicators. A revision to an already observed bar, duplicate/invalid quotes,
    changing the frozen strategy, or corrupt account state raises ValueError.
    Previously unseen backfilled dates at/before a processed date are rejected
    after initial history ingestion: recorded decisions cannot be rewritten.

    enabled=False cancels pending orders, marks new bars and equity, and creates
    no orders/fills. Consequently reactivation never replays disabled sessions.
    Orders have status pending/filled/rejected/cancelled with stable IDs, reasons
    and signal dates; fills are appended only after a strictly later open.
    """
    if not isinstance(enabled, bool):
        raise ValueError("enabled debe ser booleano.")
    rule = normalize_strategy(strategy)
    cash, quantity = _validate_account(account, rule)
    if account.get("strategy") is not None and account["strategy"] != rule:
        raise ValueError("La estrategia paper está congelada; crea otra cuenta para cambiarla.")
    weight = decimal_value(max_position_weight, "max_position_weight", positive=True)
    if weight > 1:
        raise ValueError("max_position_weight no puede superar 1; no hay apalancamiento.")
    commission = decimal_value(commission_bps, "commission_bps")
    slippage = decimal_value(slippage_bps, "slippage_bps")
    minimum = decimal_value(minimum_fee, "minimum_fee")
    if commission > 1000 or slippage > 1000:
        raise ValueError("Comisiones y deslizamiento no pueden superar 1000 pb.")
    commission /= 10000
    slippage /= 10000
    if not isinstance(bars, list) or any(not isinstance(bar, dict) or "volume" not in bar for bar in bars):
        raise ValueError("Se requieren barras OHLCV completas; no se inventa volumen.")
    incoming = [bar for bar in normalize_bars(bars) if bar["symbol"] == rule["symbol"]]
    history = normalize_bars(account["observed_bars"])
    if any(bar["symbol"] != rule["symbol"] for bar in history):
        raise ValueError("El historial paper contiene un símbolo distinto de la estrategia.")
    known = {bar["date"]: bar for bar in history}
    for bar in incoming:
        previous = known.get(bar["date"])
        if previous is not None and previous != bar:
            raise ValueError(f"La barra ya observada de {bar['date']} cambió; no se reescribe el historial paper.")
        if previous is None and history and bar["date"] <= account["last_processed_date"]:
            raise ValueError("No se pueden insertar barras antiguas después de observar una sesión paper.")
        known[bar["date"]] = bar
    market = sorted(known.values(), key=lambda bar: bar["date"])
    result = copy.deepcopy(account)
    result["strategy"] = rule
    result["enabled"] = enabled
    result["risk_limits"] = {"max_position_weight": float(weight), "commission_bps": float(commission * 10000), "slippage_bps": float(slippage * 10000), "minimum_fee": float(minimum)}
    result["observed_bars"] = [_serial_bar(bar) for bar in market]
    for warning in _WARNINGS:
        if warning not in result["warnings"]:
            result["warnings"].append(warning)
    if not enabled:
        for order in result["orders"]:
            if order["status"] == "pending":
                order.update(status="cancelled", reason="paper_disabled", cancelled_at_date=account["last_processed_date"])
    closes = [bar["close"] for bar in market]
    for index, bar in enumerate(market):
        if bar["date"] <= result["last_processed_date"]:
            continue
        day = bar["date"]
        if enabled:
            pending = next((order for order in result["orders"] if order["status"] == "pending"), None)
            if pending is not None and pending["signal_date"] < day:
                if bar["volume"] == ZERO:
                    pending.update(status="rejected", reason="zero_volume", rejected_at_date=day)
                else:
                    side = pending["side"]
                    price = bar["open"] * (1 + slippage if side == "buy" else 1 - slippage)
                    size = _buy_size(cash, price, weight, commission, minimum) if side == "buy" else quantity
                    reason = None
                    if side == "buy" and quantity:
                        reason = "position_already_open"
                    elif size <= ZERO:
                        reason = "insufficient_cash_or_position_limit" if side == "buy" else "no_position"
                    fee = max(minimum, size * price * commission)
                    if reason is None and side == "buy" and size * price + fee > cash:
                        reason = "insufficient_cash"
                    if reason is None and side == "sell" and cash + size * price < fee:
                        reason = "insufficient_cash_for_fee"
                    if reason:
                        pending.update(status="rejected", reason=reason, rejected_at_date=day)
                    else:
                        if side == "buy":
                            cash -= size * price + fee
                            quantity += size
                        else:
                            cash += size * price - fee
                            quantity -= size
                        pending.update(status="filled", filled_at_date=day, quantity=int(size), price=float(price), fee=float(fee))
                        marked_at_fill = cash + quantity * price
                        result["fills"].append({
                            "id": pending["id"] + "_fill", "order_id": pending["id"],
                            "date": day, "signal_date": pending["signal_date"], "symbol": rule["symbol"],
                            "side": side, "quantity": int(size), "price": float(price), "fee": float(fee),
                            "cash_after": float(cash), "position_after": int(quantity),
                            "position_weight_at_fill": float(quantity * price / marked_at_fill) if marked_at_fill else 0.0,
                            "simulated": True,
                        })
            wants = _desired_position(closes, index, rule)
            side = "buy" if wants and quantity == ZERO else "sell" if not wants and quantity > ZERO else None
            if side is not None:
                payload = {"strategy": rule, "signal_date": day, "side": side, "started_at_date": result["started_at_date"]}
                order_id = "paper_" + hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]
                if any(order["id"] == order_id for order in result["orders"]):
                    raise ValueError("Una señal paper intentó generar una orden duplicada.")
                result["orders"].append({
                    "id": order_id, "symbol": rule["symbol"], "side": side,
                    "status": "pending", "signal_date": day, "signal_price": float(bar["close"]),
                    "quantity": None, "target_weight": float(weight if side == "buy" else ZERO),
                    "execution": "next_observed_open", "simulated": True,
                })
        result["cash"] = float(cash)
        result["positions"] = {rule["symbol"]: int(quantity)} if quantity else {}
        result["equity"] = float(cash + quantity * bar["close"])
        result["last_price"] = float(bar["close"])
        result["last_price_date"] = day
        result["last_prices"] = {rule["symbol"]: {"date": day, "close": float(bar["close"])}}
        position_weight = quantity * bar["close"] / (cash + quantity * bar["close"]) if cash + quantity * bar["close"] else ZERO
        result["equity_curve"].append({"date": day, "equity": result["equity"], "cash": float(cash), "position_value": float(quantity * bar["close"]), "position_weight": float(position_weight), "enabled": enabled})
        if position_weight > weight:
            warning = "El peso actual supera el límite por movimiento del precio; no se ha enviado un rebalanceo automático."
            if warning not in result["warnings"]:
                result["warnings"].append(warning)
        result["last_processed_date"] = day
    # Fail before handing the caller an unpersistable or leveraged account.
    if cash < ZERO or quantity < ZERO:
        raise ValueError("El avance paper violaría efectivo o posiciones no negativos.")
    json.dumps(result, allow_nan=False)
    return result

"""Daily, long-only research on EUR bars with next-open execution.

Rules are fixed data, never model-generated executable code. Research selects
on a chronological validation partition, then evaluates the selected rule on
the untouched holdout. Neither backtests nor the LLM authorize live trading.
"""

from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal, ROUND_FLOOR
from typing import Any

import numpy as np

from .analytics import ZERO, decimal_value, iso_date, normalize_bars, symbol_value


def _integer(value: Any, field: str, minimum: int = 1, maximum: int = 1000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{field} debe ser un entero entre {minimum} y {maximum}.")
    return value


def normalize_strategy(strategy: dict) -> dict:
    if not isinstance(strategy, dict):
        raise ValueError("La estrategia debe ser un objeto.")
    kind = strategy.get("kind")
    if kind not in {"buy_hold", "sma_cross", "momentum"}:
        raise ValueError("Estrategia no admitida. Use buy_hold, sma_cross o momentum.")
    normalized = {"kind": kind, "symbol": symbol_value(strategy.get("symbol"))}
    if kind == "sma_cross":
        fast = _integer(strategy.get("fast_window", 20), "fast_window")
        slow = _integer(strategy.get("slow_window", 60), "slow_window", minimum=2)
        if fast >= slow:
            raise ValueError("fast_window debe ser menor que slow_window.")
        normalized.update(fast_window=fast, slow_window=slow)
    if kind == "momentum":
        lookback = _integer(strategy.get("lookback", 63), "lookback")
        top_k = _integer(strategy.get("top_k", 1), "top_k")
        if top_k != 1:
            raise ValueError("Momentum v0.1 es temporal sobre un símbolo; top_k debe ser 1.")
        normalized.update(lookback=lookback, top_k=1)
    return normalized


def _parameters(initial_cash, commission_bps, slippage_bps, minimum_fee, max_position_weight):
    capital = decimal_value(initial_cash, "initial_cash", positive=True)
    commission = decimal_value(commission_bps, "commission_bps")
    slippage = decimal_value(slippage_bps, "slippage_bps")
    minimum = decimal_value(minimum_fee, "minimum_fee")
    weight = decimal_value(max_position_weight, "max_position_weight", positive=True)
    if weight > 1:
        raise ValueError("max_position_weight no puede superar 1; no hay apalancamiento.")
    if commission > 1000 or slippage > 1000:
        raise ValueError("Comisiones y deslizamiento no pueden superar 1000 pb por operación.")
    return capital, commission / 10000, slippage / 10000, minimum, weight


def _want_position(closes: list[Decimal], prior_index: int, strategy: dict) -> bool:
    if prior_index < 0:
        return False
    kind = strategy["kind"]
    if kind == "buy_hold":
        return True
    if kind == "sma_cross":
        slow, fast = strategy["slow_window"], strategy["fast_window"]
        if prior_index + 1 < slow:
            return False
        end = prior_index + 1
        return sum(closes[end - fast:end], ZERO) / fast > sum(closes[end - slow:end], ZERO) / slow
    lookback = strategy["lookback"]
    return prior_index >= lookback and closes[prior_index] > closes[prior_index - lookback]


def _max_quantity(cash: Decimal, price: Decimal, commission: Decimal, minimum: Decimal,
                  weight: Decimal = Decimal("1")) -> Decimal:
    """Whole shares satisfy cash and post-fee position-weight constraints.

    Identical to the paper executor's sizing convention: the position is valued
    at its slipped fill price. Both proportional and minimum fee regimes must
    obey the cap. The weight is checked on entry, with no ongoing rebalance.
    """
    if cash <= minimum:
        return ZERO
    proportional = cash / (price * (1 + commission))
    fixed = (cash - minimum) / price
    weighted_proportional = weight * cash / (price * (1 + weight * commission))
    weighted_fixed = weight * (cash - minimum) / price
    return min(proportional, fixed, weighted_proportional, weighted_fixed).to_integral_value(rounding=ROUND_FLOOR)


def _simulate(market: list[dict], strategy: dict, start: int, stop: int, parameters: tuple) -> dict:
    initial, commission, slippage, minimum, weight = parameters
    closes = [bar["close"] for bar in market]
    cash, quantity = initial, ZERO
    trades, curve = [], []
    costs = ZERO
    prevented_sales = 0
    no_volume = 0
    for index in range(start, stop):
        bar = market[index]
        wants = _want_position(closes, index - 1, strategy)
        if bar["volume"] == ZERO:
            no_volume += 1
        elif wants and quantity == ZERO:
            price = bar["open"] * (1 + slippage)
            size = _max_quantity(cash, price, commission, minimum, weight)
            if size > ZERO:
                fee = max(minimum, size * price * commission)
                cash -= size * price + fee
                quantity = size
                costs += fee + size * (price - bar["open"])
                trades.append({"date": bar["date"], "symbol": strategy["symbol"],
                               "side": "buy", "quantity": int(size), "price": float(price), "fee": float(fee)})
        elif not wants and quantity > ZERO:
            price = bar["open"] * (1 - slippage)
            fee = max(minimum, quantity * price * commission)
            if cash + quantity * price < fee:
                prevented_sales += 1
            else:
                cash += quantity * price - fee
                costs += fee + quantity * (bar["open"] - price)
                trades.append({"date": bar["date"], "symbol": strategy["symbol"],
                               "side": "sell", "quantity": int(quantity), "price": float(price), "fee": float(fee)})
                quantity = ZERO
        curve.append({"date": bar["date"], "equity": float(cash + quantity * bar["close"])})
    return {"curve": curve, "trades": trades, "costs": float(costs),
            "prevented_sales": prevented_sales, "no_volume": no_volume,
            "final_cash": float(cash), "final_quantity": int(quantity)}


def _metrics(curve: list[dict], benchmark: list[dict], initial: Decimal, trades: list[dict], costs: float) -> dict:
    equity = np.array([float(initial)] + [point["equity"] for point in curve], dtype=float)
    previous = equity[:-1]
    daily = np.divide(np.diff(equity), previous, out=np.zeros_like(previous), where=previous > 0)
    total = equity[-1] / float(initial) - 1
    observations = len(curve)
    annualized = None
    if total > -1 and observations:
        exponent = math.log1p(total) * 252 / observations
        if exponent < 700:
            annualized = math.expm1(exponent)
    elif total == -1:
        annualized = -1.0
    deviation = float(np.std(daily, ddof=1)) if len(daily) > 1 else 0.0
    sharpe = float(np.mean(daily) / deviation * math.sqrt(252)) if deviation > 1e-15 else None
    peaks = np.maximum.accumulate(equity)
    drawdown = np.divide(equity, peaks, out=np.ones_like(equity), where=peaks > 0) - 1
    benchmark_return = benchmark[-1]["equity"] / float(initial) - 1
    return {"total_return": float(total), "annualized_return": annualized,
            "volatility": deviation * math.sqrt(252), "sharpe": sharpe,
            "max_drawdown": float(np.min(drawdown)), "trade_count": len(trades),
            "costs": costs, "benchmark_return": float(benchmark_return),
            "excess_return": float(total - benchmark_return), "observations": observations}


def _run(market: list[dict], strategy: dict, start: int, stop: int, parameters: tuple) -> dict:
    if stop - start < 2:
        raise ValueError("Se necesitan al menos dos barras en el periodo de evaluación.")
    simulation = _simulate(market, strategy, start, stop, parameters)
    benchmark = _simulate(market, {"kind": "buy_hold", "symbol": strategy["symbol"]}, start, stop, parameters)
    for point, reference in zip(simulation["curve"], benchmark["curve"], strict=True):
        point["benchmark"] = reference["equity"]
    warnings = [
        "Simulación diaria long-only EUR con acciones enteras: señal al cierre y ejecución en la siguiente apertura observada.",
        "Precios OHLC coherentes, sin ajuste automático de splits ni dividendos. La rentabilidad excluye distribuciones no incluidas en la serie.",
        "Comisión y deslizamiento configurados son supuestos; no se modelan spread variable, impacto, liquidez ni ejecuciones parciales.",
        "Benchmark buy-and-hold del mismo símbolo, capital, costes y límite de peso: mismo presupuesto de exposición. Cada periodo comienza con efectivo; posiciones finales valoradas sin liquidación forzada.",
        "El límite de peso se comprueba al comprar, después de comisiones y al precio ejecutado. El mercado puede elevar el peso posterior; no hay rebalanceo automático.",
        "Volatilidad y Sharpe usan 252 sesiones/año y tipo libre de riesgo cero; Sharpe indefinido se devuelve null. No se verifica el calendario bursátil.",
    ]
    warmup = strategy.get("slow_window", strategy.get("lookback", 0) + (strategy["kind"] == "momentum"))
    if start < warmup:
        warnings.append("La regla permanece en efectivo hasta reunir su historial previo; esas sesiones forman parte del resultado.")
    if len(simulation["curve"]) < 252:
        warnings.append("Menos de 252 sesiones: la anualización y el Sharpe son especialmente inestables.")
    if simulation["no_volume"]:
        warnings.append(f"{simulation['no_volume']} barras sin volumen: no se simulan ejecuciones en ellas.")
    if simulation["prevented_sales"]:
        warnings.append("Se bloquearon ventas cuyo efectivo no cubría la comisión mínima.")
    return {"metrics": _metrics(simulation["curve"], benchmark["curve"], parameters[0],
                                simulation["trades"], simulation["costs"]),
            "curve": simulation["curve"], "trades": simulation["trades"], "warnings": warnings,
            "final_cash": simulation["final_cash"], "final_quantity": simulation["final_quantity"],
            "strategy": strategy, "max_position_weight": float(parameters[4])}


def backtest(bars: list[dict], strategy: dict, initial_cash=10000, commission_bps=5,
             slippage_bps=5, minimum_fee=1.25, *, evaluation_start: str | None = None,
             max_position_weight=1.0) -> dict:
    """Evaluate from the first observed session on/after evaluation_start.

    Earlier bars provide indicator history only. Every evaluation starts with
    initial_cash and zero holdings; no earlier trades or equity are reused.
    A weekend/holiday start advances to the next observed bar, with a warning.
    Strategy and benchmark share the same maximum entry weight after fees.
    """
    rule = normalize_strategy(strategy)
    market = [bar for bar in normalize_bars(bars) if bar["symbol"] == rule["symbol"]]
    parameters = _parameters(initial_cash, commission_bps, slippage_bps, minimum_fee, max_position_weight)
    start = 0
    if evaluation_start is not None:
        requested = iso_date(evaluation_start)
        start = next((index for index, bar in enumerate(market) if bar["date"] >= requested), len(market))
    result = _run(market, rule, start, len(market), parameters)
    if evaluation_start is not None and market[start]["date"] != evaluation_start:
        result["warnings"].append(f"Inicio solicitado {evaluation_start}: evaluación desde la primera barra disponible, {market[start]['date']}.")
    return result


def _period(market: list[dict], start: int, stop: int) -> dict:
    return {"start": market[start]["date"], "end": market[stop - 1]["date"], "observations": stop - start}


def run_research(bars: list[dict], candidates: list[dict], initial_cash=10000, commission_bps=5,
                 slippage_bps=5, minimum_fee=1.25, max_position_weight=1.0) -> dict:
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 30:
        raise ValueError("La investigación requiere entre 1 y 30 candidatos definidos antes de evaluar el holdout.")
    rules = [normalize_strategy(candidate) for candidate in candidates]
    if len({json.dumps(rule, sort_keys=True) for rule in rules}) != len(rules):
        raise ValueError("La lista contiene estrategias candidatas duplicadas.")
    market = normalize_bars(bars)
    parameters = _parameters(initial_cash, commission_bps, slippage_bps, minimum_fee, max_position_weight)
    symbols = sorted({rule["symbol"] for rule in rules})
    grouped = {symbol: [bar for bar in market if bar["symbol"] == symbol] for symbol in symbols}
    common_dates = set.intersection(*({bar["date"] for bar in grouped[symbol]} for symbol in symbols))
    if len(common_dates) < 100:
        raise ValueError("La investigación necesita al menos 100 fechas comunes (60/20/20); es un mínimo técnico, no evidencia suficiente para operar.")
    aligned = {symbol: [bar for bar in grouped[symbol] if bar["date"] in common_dates] for symbol in symbols}
    reference = aligned[symbols[0]]
    count = len(reference)
    train_end = int(count * 0.6)
    validation_end = int(count * 0.8)
    results = []
    for rule in rules:
        validation = _run(aligned[rule["symbol"]], rule, train_end, validation_end, parameters)
        results.append({"strategy": rule, "validation_metrics": validation["metrics"]})
    # Stable input-order ties; the holdout is not consulted to select a rule.
    winner = max(results, key=lambda result: (result["validation_metrics"]["excess_return"],
                                              result["validation_metrics"]["total_return"]))["strategy"]
    selected_market = aligned[winner["symbol"]]
    holdout = _run(selected_market, winner, validation_end, count, parameters)
    full = _run(selected_market, winner, 0, count, parameters)
    sensitivity = []
    for multiplier in (0.5, 1.0, 2.0):
        varied = (parameters[0], parameters[1] * Decimal(str(multiplier)),
                  parameters[2] * Decimal(str(multiplier)), parameters[3] * Decimal(str(multiplier)), parameters[4])
        variant = _run(selected_market, winner, validation_end, count, varied)
        sensitivity.append({"cost_multiplier": multiplier, "period": "test", "metrics": variant["metrics"]})
    serializable = [{key: str(value) if isinstance(value, Decimal) else value for key, value in bar.items()}
                    for bar in market]
    data_hash = hashlib.sha256(json.dumps(serializable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    warnings = [
        "Selección por exceso de rentabilidad neta frente al benchmark en validación; desempate por retorno neto y orden de candidatos. El entrenamiento aporta únicamente historial a reglas fijas.",
        "Holdout evaluado solo para el ganador; cambiar candidatos después de leerlo contamina la prueba. full_result es exploratorio y no fuera de muestra.",
        "La sensibilidad de costes reevalúa únicamente al ganador congelado en el holdout; no ajusta ni vuelve a seleccionar la regla.",
        "Estas pruebas no demuestran rentabilidad futura ni autorizan órdenes reales. Dos días no establecen validez estadística.",
        "No se corrigen sesgos de supervivencia ni selección de instrumentos; la calidad, frecuencia y ajustes corporativos del dataset requieren revisión.",
    ]
    discarded = sum(len(grouped[symbol]) - len(aligned[symbol]) for symbol in symbols)
    if discarded:
        warnings.append(f"Se excluyeron {discarded} barras fuera del calendario común; no se rellenaron precios.")
    return {"selected_strategy": winner, "candidate_results": results,
            "train_period": _period(reference, 0, train_end),
            "validation_period": _period(reference, train_end, validation_end),
            "test_period": _period(reference, validation_end, count),
            "out_of_sample": holdout, "full_result": full, "sensitivity": sensitivity,
            "data_hash": data_hash, "warnings": warnings,
            "max_position_weight": float(parameters[4])}

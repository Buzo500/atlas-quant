"""Deterministic research gates; no model output can authorize an order.

The thresholds are configurable heuristics, not a statistical proof of alpha.
Eligibility in this version means *local paper* only, never a live mandate.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


DEFAULT_POLICY = {
    "min_oos_observations": 126,
    "min_trades": 10,
    "min_sharpe": 0.5,
    "max_drawdown": 0.15,
    "min_excess_return": 0.0,
    "min_forward_sessions": 20,
    "requested_hours": 48,
}

_LIMITATIONS = [
    "Los umbrales son filtros orientativos; no demuestran rentabilidad futura ni significación estadística.",
    "Dos días permiten comprobar el funcionamiento, pero no validar una estrategia diaria.",
    "La elegibilidad permite únicamente simulación local. Esta versión no habilita dinero real.",
    "La selección de estrategias introduce sesgo por pruebas múltiples; el periodo fuera de muestra no debe reutilizarse para ajustar parámetros.",
]


def _number(value: Any) -> bool:
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def _clean(value: Any) -> Any:
    """Keep diagnostics JSON-safe, including when the rejected input has NaN."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, Mapping):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    return value


def _finite_tree(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(_finite_tree(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(_finite_tree(v) for v in value)
    return True


def evaluate_evidence(
    research: dict, observation: dict, policy: dict | None = None
) -> dict:
    """Evaluate OOS metrics, stressed costs and genuinely new sessions.

    ``research.out_of_sample.metrics`` contains ``observations``, ``trade_count``,
    ``sharpe``, ``max_drawdown`` (fraction, compared by absolute value), and ``excess_return``.
    ``research.sensitivity`` is a list of ``{cost_multiplier, metrics}``.
    Missing, malformed or non-finite inputs fail closed. Insufficient history or
    forward observations return ``observe``; failing performance returns
    ``rejected``. ``eligible_paper`` never authorizes broker orders.
    """
    checks: list[dict] = []

    def check(name: str, passed: bool, actual: Any, required: Any, reason: str) -> bool:
        checks.append({
            "name": name, "passed": bool(passed), "actual": _clean(actual),
            "required": required, "reason": reason,
        })
        return bool(passed)

    def result(decision: str) -> dict:
        return {
            "passed": decision == "eligible_paper", "decision": decision,
            "checks": checks, "limitations": list(_LIMITATIONS),
        }

    if not isinstance(policy, (dict, type(None))):
        check("valid_policy", False, None, "objeto de límites", "La política no es válida.")
        return result("rejected")
    resolved = {**DEFAULT_POLICY, **(policy or {})}
    integer_keys = ("min_oos_observations", "min_trades", "min_forward_sessions")
    valid_policy = all(
        type(resolved[k]) is int and resolved[k] >= 1 for k in integer_keys
    ) and all(_number(resolved[k]) for k in DEFAULT_POLICY)
    valid_policy = valid_policy and (
        0 < resolved["max_drawdown"] <= 1
        and 0 < resolved["requested_hours"] <= 24 * 365
        and resolved["min_sharpe"] >= 0
        and resolved["min_excess_return"] >= 0
    )
    if not check("valid_policy", valid_policy, resolved, "límites finitos, positivos y sin apalancamiento", "No se aceptan umbrales inválidos."):
        return result("rejected")

    if not check(
        "finite_data",
        isinstance(research, dict) and isinstance(observation, dict)
        and _finite_tree(research) and _finite_tree(observation),
        None, "datos y métricas finitos", "NaN e infinito invalidan la evaluación.",
    ):
        return result("rejected")

    metrics = research.get("out_of_sample", {}).get("metrics", {}) if isinstance(research.get("out_of_sample"), dict) else {}

    def valid_metrics(m: Any) -> bool:
        return isinstance(m, dict) and all(
            _number(m.get(key)) for key in ("observations", "trade_count", "sharpe", "max_drawdown", "excess_return")
        ) and all(type(m[k]) is int and m[k] >= 0 for k in ("observations", "trade_count")) and abs(m["max_drawdown"]) <= 1

    if not check("valid_oos_metrics", valid_metrics(metrics), metrics, "métricas completas fuera de muestra", "El drawdown es una fracción; se compara su magnitud. Los conteos son enteros."):
        return result("rejected")
    enough_oos = check(
        "oos_observations", metrics["observations"] >= resolved["min_oos_observations"],
        metrics["observations"], resolved["min_oos_observations"], "Se necesitan observaciones fuera de muestra suficientes.",
    )
    enough_trades = check(
        "trade_count", metrics["trade_count"] >= resolved["min_trades"],
        metrics["trade_count"], resolved["min_trades"], "Un número pequeño de operaciones deja gran incertidumbre.",
    )
    performance = [
        check("sharpe", metrics["sharpe"] >= resolved["min_sharpe"], metrics["sharpe"], resolved["min_sharpe"], "Sharpe neto mínimo fuera de muestra."),
        check("max_drawdown", abs(metrics["max_drawdown"]) <= resolved["max_drawdown"], metrics["max_drawdown"], resolved["max_drawdown"], "Pérdida máxima histórica permitida, en valor absoluto."),
        check("excess_return", metrics["excess_return"] >= resolved["min_excess_return"], metrics["excess_return"], resolved["min_excess_return"], "Rentabilidad neta relativa al benchmark en el mismo periodo."),
    ]

    sensitivity = research.get("sensitivity")
    valid_sensitivity = isinstance(sensitivity, list) and len(sensitivity) > 0 and all(
        isinstance(s, dict) and _number(s.get("cost_multiplier")) and s["cost_multiplier"] >= 0
        and valid_metrics(s.get("metrics")) for s in sensitivity
    )
    valid_sensitivity = valid_sensitivity and any(s["cost_multiplier"] > 1 for s in sensitivity)
    if not check("valid_cost_stress", valid_sensitivity, sensitivity, "al menos un escenario con costes superiores", "La robustez exige recalcular el periodo fuera de muestra con costes mayores."):
        return result("rejected")
    stress_passed = all(
        s["metrics"]["excess_return"] >= resolved["min_excess_return"]
        and abs(s["metrics"]["max_drawdown"]) <= resolved["max_drawdown"]
        and s["metrics"]["observations"] == metrics["observations"]
        for s in sensitivity
    )
    performance.append(check(
        "cost_stress", stress_passed,
        [{"cost_multiplier": s["cost_multiplier"], "excess_return": s["metrics"]["excess_return"], "max_drawdown": s["metrics"]["max_drawdown"]} for s in sensitivity],
        {"min_excess_return": resolved["min_excess_return"], "max_drawdown": resolved["max_drawdown"]},
        "Todos los escenarios deben superar los filtros con las mismas observaciones.",
    ))

    valid_observation = (
        _number(observation.get("elapsed_hours")) and observation["elapsed_hours"] >= 0
        and type(observation.get("new_sessions")) is int and observation["new_sessions"] >= 0
        and observation.get("source_kind") in ("synthetic", "observed")
        and type(observation.get("reconciled")) is bool
    )
    if not check("valid_observation", valid_observation, observation, "horas, sesiones, origen y conciliación válidos", "No se puede asumir observación si faltan metadatos."):
        return result("rejected")
    forward = [
        check("observation_hours", observation["elapsed_hours"] >= resolved["requested_hours"], observation["elapsed_hours"], resolved["requested_hours"], "Cumplir el tiempo solicitado no sustituye observar nuevas sesiones."),
        check("new_forward_sessions", observation["new_sessions"] >= resolved["min_forward_sessions"], observation["new_sessions"], resolved["min_forward_sessions"], "Deben ser sesiones nuevas posteriores al inicio; releer un histórico no añade sesiones."),
        check("observed_source", observation["source_kind"] == "observed", observation["source_kind"], "observed", "Los precios sintéticos sirven para demos y no son evidencia de mercado."),
        check("reconciled", observation["reconciled"] is True, observation["reconciled"], True, "Las observaciones y posiciones simuladas deben estar conciliadas."),
    ]
    if observation["new_sessions"] >= resolved["min_forward_sessions"]:
        forward_metrics = observation.get("forward_metrics")
        valid_forward = (
            isinstance(forward_metrics, dict)
            and all(_number(forward_metrics.get(k)) for k in ("observations", "total_return", "max_drawdown", "excess_return"))
            and type(forward_metrics.get("observations")) is int
            and forward_metrics["observations"] >= resolved["min_forward_sessions"]
            and forward_metrics["observations"] <= observation["new_sessions"]
            and abs(forward_metrics["max_drawdown"]) <= 1
            and forward_metrics["total_return"] >= -1
        )
        if not check("valid_forward_metrics", valid_forward, forward_metrics, "rendimiento sobre sesiones nuevas tras congelar la estrategia", "Contar sesiones no basta: se exige medir el rendimiento prospectivo."):
            return result("rejected")
        performance.append(check(
            "forward_performance",
            forward_metrics["excess_return"] >= resolved["min_excess_return"]
            and abs(forward_metrics["max_drawdown"]) <= resolved["max_drawdown"],
            forward_metrics,
            {"min_excess_return": resolved["min_excess_return"], "max_drawdown": resolved["max_drawdown"]},
            "La estrategia congelada debe respetar los filtros también en las sesiones prospectivas.",
        ))
    else:
        forward.append(check("forward_performance", False, None, "rendimiento prospectivo suficiente", "Aún no hay suficientes sesiones nuevas para evaluar este filtro."))
    if not all(performance):
        return result("rejected")
    if not (enough_oos and enough_trades and all(forward)):
        return result("observe")
    return result("eligible_paper")

"""Transactional experiment controls and paper risk settings, independent of HTTP."""
from .paper import advance_paper


DEFAULT_SETTINGS = {"id": "main", "kill_switch": True, "max_position_weight": 0.25,
                    "mode": "paper", "live_available": False}
ACTIVE_STATUSES = {"queued", "running", "observing", "eligible_paper"}


class WorkStopped(Exception):
    """Cooperative stop at a safe boundary; never an experiment failure."""


def cancel_pending(job):
    for order in (job.get("paper_account") or {}).get("orders", []):
        if order.get("status") == "pending":
            order["status"] = "cancelled"


def skip_disabled_sessions(tx, job):
    if job.get("paper_account"):
        dataset = tx.get("dataset", job["dataset_id"])
        job["paper_account"] = advance_paper(
            job["paper_account"], dataset["bars"], job["research"]["selected_strategy"],
            enabled=False, **{k: v for k, v in job["costs"].items() if k != "initial_cash"})


def control_experiment(store, ident, action):
    def apply(tx):
        job = tx.get("experiment", ident)
        if not job:
            raise ValueError("Experimento no encontrado.")
        if action == "cancel" and job["status"] in ACTIVE_STATUSES | {"paused", "interrupted"}:
            job["status"] = "cancelled"
        elif action == "pause" and job["status"] in ACTIVE_STATUSES:
            job["resume_status"] = job["status"]
            job["status"] = "paused"
        elif action == "resume" and job["status"] == "paused":
            if job.get("execution_active"):
                raise ValueError("La pausa está solicitada; espera a que termine la operación en curso para reanudar.")
            if job.get("reserved_usd", 0):
                raise ValueError("Existe una reserva de API sin resolver; no se permite reintentar automáticamente.")
            skip_disabled_sessions(tx, job)
            previous = job.pop("resume_status", "observing")
            job["status"] = "queued" if previous == "running" else previous
        elif (action, job["status"]) not in {("cancel", "cancelled"), ("pause", "paused")}:
            raise ValueError("Transición no permitida. Los errores de API no se reintentan automáticamente.")
        job["control_requested"] = action if job.get("execution_active") and action != "resume" else None
        cancel_pending(job)
        return tx.put("experiment", job, "experiment." + job["status"])
    return store.atomic(apply)


def update_settings(store, values):
    """Merge requested fields with current settings in the same transaction as paper controls."""
    if not values:
        raise ValueError("Indica al menos un ajuste que quieras cambiar.")
    def apply(tx):
        previous = tx.get("settings", "main", DEFAULT_SETTINGS)
        config = {**previous, **values}
        for job in tx.list("experiment"):
            if not job.get("paper_account"):
                continue
            weight = job["costs"].get("max_position_weight", 1)
            was_enabled = not previous["kill_switch"] and weight <= previous["max_position_weight"]
            will_enable = not config["kill_switch"] and weight <= config["max_position_weight"]
            if (previous["kill_switch"] and not config["kill_switch"]) or (not was_enabled and will_enable):
                skip_disabled_sessions(tx, job)
            # A limit change also invalidates orders sized under the previous policy.
            if config["kill_switch"] or config["max_position_weight"] != previous["max_position_weight"]:
                cancel_pending(job)
            tx.put("experiment", job, "paper.risk_control_applied")
        return tx.put("settings", config, "risk.settings_changed")
    return store.atomic(apply)

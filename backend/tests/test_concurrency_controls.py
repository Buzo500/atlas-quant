"""Concurrent controls at real await boundaries; providers are local fakes."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from threading import Event

import pytest
import httpx

from atlas_quant import ai, controls, service as service_module
from atlas_quant.paper import advance_paper, new_account
from atlas_quant.service import Service
from atlas_quant.store import Store
from atlas_quant.worker_lock import WorkerAlreadyRunning

from test_service import add_dataset, history, local_service, price, request, research_result


async def wait_started(event):
    assert await asyncio.to_thread(event.wait, 5), "Worker did not reach the controlled boundary"


def cpu_barrier(monkeypatch, *, function="run_research", result_factory=research_result):
    started, release = Event(), Event()
    calls = []

    def computation(*args, checkpoint=None, **kwargs):
        calls.append(args)
        started.set()
        assert release.wait(5), "Test did not release the worker"
        if checkpoint:
            checkpoint()
        return result_factory()

    monkeypatch.setattr(service_module, function, computation)
    return started, release, calls


def ai_job(service, monkeypatch):
    monkeypatch.setattr(ai, "provider_status", lambda: [
        {"provider": "openai", "configured": True, "models": [{"id": "offline-fake"}]}])
    dataset = add_dataset(service)
    return service.create_experiment(request(dataset["id"], provider="openai", model="offline-fake"))


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_control_during_cpu_returns_before_completion_and_cannot_be_overwritten(local_service, monkeypatch, action):
    dataset = add_dataset(local_service)
    job = local_service.create_experiment(request(dataset["id"]))
    started, release, calls = cpu_barrier(monkeypatch)

    async def scenario():
        running = asyncio.create_task(local_service.tick())
        try:
            await wait_started(started)
            controlled = local_service.control(job["id"], action)
            assert controlled["status"] == ("paused" if action == "pause" else "cancelled")
            assert controlled["execution_active"] is True
            assert controlled["control_requested"] == action
            assert not running.done()
            if action == "pause":
                with pytest.raises(ValueError, match="operación en curso"):
                    local_service.control(job["id"], "resume")
        finally:
            release.set()
            await asyncio.wait_for(running, 5)
        saved = local_service.store.get("experiment", job["id"])
        assert saved["status"] == ("paused" if action == "pause" else "cancelled")
        assert saved["execution_active"] is False
        assert saved["control_requested"] is None
        assert saved["research"] is None
        assert saved["summary"] is None
        assert saved["paper_account"] is None
        await local_service.tick()
        assert len(calls) == 1

    asyncio.run(scenario())


def test_pause_during_ai_settles_and_keeps_plan_without_repeating_paid_stage(local_service, monkeypatch):
    job = ai_job(local_service, monkeypatch)
    calls = []

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def propose(**kwargs):
            calls.append("plan")
            started.set()
            await release.wait()
            return {"plan": {"hypothesis": "Offline plan", "risks": [], "candidates": [
                {"kind": "buy_hold", "symbol": "ETF"}]}, "usage": {"estimated_cost_usd": .2}}

        async def summarize(**kwargs):
            calls.append("summary")
            return {"summary": "Offline summary", "limitations": [], "provider": "openai",
                    "recommendation": "continue_observation", "usage": {"estimated_cost_usd": .1}}

        monkeypatch.setattr(ai, "propose_strategies", propose)
        monkeypatch.setattr(ai, "summarize_research", summarize)
        running = asyncio.create_task(local_service.tick())
        try:
            await asyncio.wait_for(started.wait(), 5)
            controlled = local_service.control(job["id"], "pause")
            assert controlled["reserved_usd"] == 1
            assert controlled["execution_active"] is True
        finally:
            release.set()
            await asyncio.wait_for(running, 5)
        paused = local_service.store.get("experiment", job["id"])
        assert paused["status"] == "paused"
        assert paused["execution_active"] is False
        assert paused["spent_usd"] == pytest.approx(.2)
        assert paused["reserved_usd"] == 0
        assert paused["plan"]["hypothesis"] == "Offline plan"
        assert paused["research"] is None
        local_service.control(job["id"], "resume")
        await local_service.tick()
        resumed = local_service.store.get("experiment", job["id"])
        assert resumed["status"] == "observing"
        assert resumed["spent_usd"] == pytest.approx(.3)
        assert resumed["reserved_usd"] == 0
        assert calls == ["plan", "summary"]

    asyncio.run(scenario())


def test_cancel_during_ai_settles_cost_without_restoring_status_or_calling_summary(local_service, monkeypatch):
    job = ai_job(local_service, monkeypatch)
    calls = []

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def propose(**kwargs):
            calls.append("plan")
            started.set()
            await release.wait()
            return {"plan": {"candidates": [{"kind": "buy_hold", "symbol": "ETF"}]},
                    "usage": {"estimated_cost_usd": .2}}

        async def summarize(**kwargs):
            calls.append("summary")
            raise AssertionError("A cancelled experiment must not start another paid call")

        monkeypatch.setattr(ai, "propose_strategies", propose)
        monkeypatch.setattr(ai, "summarize_research", summarize)
        running = asyncio.create_task(local_service.tick())
        try:
            await asyncio.wait_for(started.wait(), 5)
            controlled = local_service.control(job["id"], "cancel")
            assert controlled["status"] == "cancelled"
            assert controlled["reserved_usd"] == 1
        finally:
            release.set()
            await asyncio.wait_for(running, 5)
        cancelled = local_service.store.get("experiment", job["id"])
        assert cancelled["status"] == "cancelled"
        assert cancelled["spent_usd"] == pytest.approx(.2)
        assert cancelled["reserved_usd"] == 0
        assert cancelled["execution_active"] is False
        assert cancelled.get("plan") is None
        assert cancelled["research"] is None
        await local_service.tick()
        assert calls == ["plan"]

    asyncio.run(scenario())


def test_uncertain_ai_failure_retains_reservation_and_cannot_resume_or_auto_retry(local_service, monkeypatch):
    job = ai_job(local_service, monkeypatch)
    calls = []

    async def propose(**kwargs):
        calls.append("plan")
        raise RuntimeError("Fake transport failed without a confirmed provider outcome")

    monkeypatch.setattr(ai, "propose_strategies", propose)
    asyncio.run(local_service.tick())
    saved = local_service.store.get("experiment", job["id"])
    assert saved["status"] == "interrupted"
    assert saved["reserved_usd"] == 1
    assert saved["spent_usd"] == 0
    assert saved["execution_active"] is False
    with pytest.raises(ValueError):
        local_service.control(job["id"], "resume")
    reopened = Store(local_service.store.path)
    reopened.recover()
    asyncio.run(Service(reopened).tick())
    assert calls == ["plan"]
    assert reopened.get("experiment", job["id"])["reserved_usd"] == 1


def paper_job(service, dataset, *, status="eligible_paper"):
    job = service.create_experiment(request(dataset["id"], costs={
        "initial_cash": 10000, "commission_bps": 5, "slippage_bps": 5,
        "minimum_fee": 1.25, "max_position_weight": .25}))
    # Seed an already-running legacy account; D3 gates for new accounts have their own integration tests.
    job.pop("quality_policy", None)
    rule = {"kind": "buy_hold", "symbol": "ETF"}
    account = advance_paper(new_account(started_at_date="2026-09-01"),
        [b for b in dataset["bars"] if b["date"] <= "2026-09-02"], rule, enabled=True)
    job.update(status=status, research=research_result(), observation_started_at="2026-09-02T00:00:00+00:00",
               paper_account=account, cutoff="2026-09-03", phase="forward_observation")
    service.store.put("experiment", job)
    assert any(order["status"] == "pending" for order in account["orders"])
    assert account["fills"] == []
    return job


def test_kill_switch_during_observation_blocks_pending_fills_and_skips_disabled_sessions(local_service, monkeypatch):
    dataset = add_dataset(local_service, history() + [price(f"2026-09-0{i}", 120 + i) for i in range(1, 6)])
    job = paper_job(local_service, dataset)
    local_service.store.put("settings", {**controls.DEFAULT_SETTINGS, "kill_switch": False})
    started, release, _ = cpu_barrier(monkeypatch, function="backtest",
                                    result_factory=lambda: research_result()["out_of_sample"])
    monkeypatch.setattr(service_module, "evaluate_evidence", lambda *args: {"passed": True, "checks": []})

    async def scenario():
        running = asyncio.create_task(local_service.tick())
        try:
            await wait_started(started)
            local_service.update_settings({"kill_switch": True, "max_position_weight": .25})
            halted = local_service.store.get("experiment", job["id"])
            assert all(order["status"] == "cancelled" for order in halted["paper_account"]["orders"])
            assert not running.done()
        finally:
            release.set()
            await asyncio.wait_for(running, 5)
        saved = local_service.store.get("experiment", job["id"])
        assert saved["status"] == "eligible_paper"
        assert saved["paper_account"]["fills"] == []
        assert saved["paper_account"]["enabled"] is False
        assert saved["paper_account"]["last_processed_date"] == "2026-09-05"
        local_service.update_settings({"kill_switch": False, "max_position_weight": .25})
        await local_service.tick()
        assert local_service.store.get("experiment", job["id"])["paper_account"]["fills"] == []

    asyncio.run(scenario())


def test_settings_failure_rolls_back_all_accounts_settings_and_audit(local_service, monkeypatch):
    dataset = add_dataset(local_service, history() + [price("2026-09-01", 120), price("2026-09-02", 121)])
    paper_job(local_service, dataset)
    paper_job(local_service, dataset)
    local_service.store.put("settings", dict(controls.DEFAULT_SETTINGS))
    before_jobs = deepcopy(local_service.store.list("experiment"))
    before_settings = local_service.settings()
    before_audit = local_service.store.audit_list()
    calls = []
    real_advance = controls.advance_paper

    def fail_second(*args, **kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise ValueError("Invalid second account fixture")
        return real_advance(*args, **kwargs)

    monkeypatch.setattr(controls, "advance_paper", fail_second)
    with pytest.raises(ValueError, match="second account"):
        local_service.update_settings({"kill_switch": False, "max_position_weight": .25})
    assert len(calls) == 2
    assert local_service.store.list("experiment") == before_jobs
    assert local_service.settings() == before_settings
    assert local_service.store.audit_list() == before_audit


def test_two_service_instances_do_not_execute_the_same_queued_job(local_service, monkeypatch):
    dataset = add_dataset(local_service)
    job = local_service.create_experiment(request(dataset["id"]))
    competitor = Service(Store(local_service.store.path))
    started, release, calls = cpu_barrier(monkeypatch)

    async def scenario():
        running = asyncio.create_task(local_service.tick())
        try:
            await wait_started(started)
            await asyncio.wait_for(competitor.tick(), 1)
            assert len(calls) == 1
            assert not running.done()
        finally:
            release.set()
            await asyncio.wait_for(running, 5)
        await competitor.tick()
        assert len(calls) == 1
        assert competitor.store.get("experiment", job["id"])["status"] == "observing"

    asyncio.run(scenario())


def test_provider_error_during_pause_is_terminal_and_cannot_repeat_paid_plan(local_service, monkeypatch):
    job = ai_job(local_service, monkeypatch)
    calls = []

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def propose(**kwargs):
            calls.append("plan")
            started.set()
            await release.wait()
            raise ai.AIError("timeout", "Fake provider timeout", may_be_charged=True, reserved_cost_usd=.4)

        monkeypatch.setattr(ai, "propose_strategies", propose)
        running = asyncio.create_task(local_service.tick())
        try:
            await asyncio.wait_for(started.wait(), 5)
            local_service.control(job["id"], "pause")
            with pytest.raises(ValueError, match="operación en curso"):
                local_service.control(job["id"], "resume")
        finally:
            release.set()
            await asyncio.wait_for(running, 5)
        saved = local_service.store.get("experiment", job["id"])
        assert saved["status"] == "failed"
        assert saved["spent_usd"] == pytest.approx(.4)
        assert saved["reserved_usd"] == 0
        assert saved["execution_active"] is False
        assert saved.get("plan") is None
        with pytest.raises(ValueError):
            local_service.control(job["id"], "resume")
        await local_service.tick()
        assert calls == ["plan"]

    asyncio.run(scenario())


def test_worker_shutdown_drains_cpu_thread_before_releasing_execution(local_service, monkeypatch):
    dataset = add_dataset(local_service)
    job = local_service.create_experiment(request(dataset["id"]))
    started, release, thread_done = Event(), Event(), Event()

    def computation(*args, checkpoint=None, **kwargs):
        started.set()
        try:
            assert release.wait(5)
            checkpoint()
            return research_result()
        finally:
            thread_done.set()

    monkeypatch.setattr(service_module, "run_research", computation)

    async def scenario():
        running = asyncio.create_task(local_service.tick())
        try:
            await wait_started(started)
            running.cancel()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert not thread_done.is_set()
            assert not running.done()
            assert local_service.store.get("experiment", job["id"])["execution_active"] is True
        finally:
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(running, 5)
        assert thread_done.is_set()
        saved = local_service.store.get("experiment", job["id"])
        assert saved["status"] == "interrupted"
        assert saved["execution_active"] is False
        assert saved["research"] is None
        await Service(Store(local_service.store.path)).tick()
        assert local_service.store.get("experiment", job["id"])["status"] == "interrupted"

    asyncio.run(scenario())


@pytest.mark.parametrize("action", ["pause", "cancel"])
def test_http_control_responds_while_cpu_is_still_running(local_service, monkeypatch, action):
    from atlas_quant.app import create_app

    app = create_app(local_service.store.path.parent, run_worker=False)
    service = app.state.service
    dataset = add_dataset(service)
    started, release, _ = cpu_barrier(monkeypatch)

    async def scenario():
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver",
                                        headers={"x-atlas-client": "local-v1"}) as client:
                created = await client.post("/api/experiments", json=request(dataset["id"]))
                assert created.status_code == 201, created.text
                ident = created.json()["id"]
                running = asyncio.create_task(service.tick())
                try:
                    await wait_started(started)
                    response = await asyncio.wait_for(client.post(f"/api/experiments/{ident}/control",
                                                                  json={"action": action}), 1)
                    assert response.status_code == 200, response.text
                    assert response.json()["status"] == ("paused" if action == "pause" else "cancelled")
                    assert response.json()["execution_active"] is True
                    assert response.json()["control_requested"] == action
                    assert not running.done()
                finally:
                    release.set()
                    await asyncio.wait_for(running, 5)

    asyncio.run(scenario())


def test_second_lifespan_is_rejected_before_recovering_the_live_owners_jobs(local_service):
    from atlas_quant.app import create_app

    first = create_app(local_service.store.path.parent, run_worker=False)
    second = create_app(local_service.store.path.parent, run_worker=False)

    async def scenario():
        async with first.router.lifespan_context(first):
            local_service.store.put("experiment", {"id": "active-owner-job", "status": "running",
                "execution_active": True, "execution_token": "live-owner", "reserved_usd": .7})
            before = local_service.store.get("experiment", "active-owner-job")
            with pytest.raises(WorkerAlreadyRunning):
                async with second.router.lifespan_context(second):
                    pytest.fail("A second lifespan must not start on the same database")
            assert local_service.store.get("experiment", "active-owner-job") == before
        async with second.router.lifespan_context(second):
            recovered = local_service.store.get("experiment", "active-owner-job")
            assert recovered["status"] == "interrupted"
            assert recovered["execution_active"] is False
            assert recovered["reserved_usd"] == .7
            assert "execution_token" not in recovered

    asyncio.run(scenario())


def test_relaxing_weight_limit_skips_blocked_sessions_and_only_fills_after_a_new_signal(local_service, monkeypatch):
    dataset = add_dataset(local_service, history() + [price("2026-09-01", 120), price("2026-09-02", 121)])
    job = paper_job(local_service, dataset)
    local_service.store.put("settings", {**controls.DEFAULT_SETTINGS, "kill_switch": False})
    monkeypatch.setattr(service_module, "evaluate_evidence", lambda *args: {"passed": True, "checks": []})

    # A pending September 2 signal was sized under the former .25 policy.
    local_service.update_settings({"kill_switch": False, "max_position_weight": .1})
    blocked = local_service.store.get("experiment", job["id"])
    assert blocked["paper_account"]["orders"][0]["status"] == "cancelled"
    dataset = local_service.save_dataset([*dataset["bars"], price("2026-09-03", 122)],
        dataset["name"], "observed", dataset["source"], ident=dataset["id"])

    # No observation tick occurred while blocked. Rearming must still consume
    # that session with execution disabled, rather than trade it retrospectively.
    local_service.update_settings({"kill_switch": False, "max_position_weight": .25})
    rearmed = local_service.store.get("experiment", job["id"])["paper_account"]
    assert rearmed["last_processed_date"] == "2026-09-03"
    assert rearmed["fills"] == []
    assert not any(order["status"] == "pending" for order in rearmed["orders"])

    dataset = local_service.save_dataset([*dataset["bars"], price("2026-09-04", 123)],
        dataset["name"], "observed", dataset["source"], ident=dataset["id"])
    asyncio.run(local_service.tick())
    signalled = local_service.store.get("experiment", job["id"])["paper_account"]
    assert signalled["fills"] == []
    pending = [order for order in signalled["orders"] if order["status"] == "pending"]
    assert len(pending) == 1
    assert pending[0]["signal_date"] == "2026-09-04"

    local_service.save_dataset([*dataset["bars"], price("2026-09-05", 124)],
        dataset["name"], "observed", dataset["source"], ident=dataset["id"])
    asyncio.run(local_service.tick())
    executed = local_service.store.get("experiment", job["id"])["paper_account"]
    assert len(executed["fills"]) == 1
    assert executed["fills"][0]["date"] == "2026-09-05"
    assert executed["fills"][0]["order_id"] == pending[0]["id"]

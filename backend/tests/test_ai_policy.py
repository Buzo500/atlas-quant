"""AI providers are mocked: this suite never makes paid model calls."""

import asyncio
import copy
import json

import httpx
import pytest

from atlas_quant.ai import AIError, DEFAULT_MODELS, propose_strategies, provider_status, summarize_research
from atlas_quant.gates import evaluate_evidence


PLAN = {
    "hypothesis": "Una tendencia persistente puede justificar probar el cruce de medias.",
    "horizon_hours": 48,
    "candidates": [{"kind": "sma_cross", "symbol": "SPY", "fast_window": 20, "slow_window": 80, "rationale": "Hipótesis pendiente de contrastar."}],
    "risks": ["Sobreajuste y costes de transacción."],
}
SUMMARY = {
    "summary": "Los resultados requieren observación adicional.",
    "limitations": ["Dos días no bastan para validar rentabilidad."],
    "recommendation": "continue_observation",
}


def _reply(provider, content):
    usage = {"input_tokens": 500, "output_tokens": 250}
    if provider == "openai":
        return {"status": "completed", "output": [{"type": "message", "status": "completed", "role": "assistant", "content": [{"type": "output_text", "text": json.dumps(content)}]}], "usage": usage}
    return {"type": "message", "stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps(content)}], "usage": usage}


@pytest.fixture(autouse=True)
def fake_keys(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-not-a-real-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key-not-a-real-secret")


def _run_proposal(handler, provider="openai", budget=1.0, **kwargs):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await propose_strategies("Prueba tendencia", {"symbols": ["SPY"]}, provider, budget_usd=budget, client=client, **kwargs)
    return asyncio.run(run())


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_provider_payload_and_validated_plan(provider):
    calls = []

    def handler(request):
        calls.append(request)
        payload = json.loads(request.content)
        assert payload["model"] == DEFAULT_MODELS[provider]
        assert "tools" not in payload
        assert "base_url" not in payload
        if provider == "openai":
            assert str(request.url) == "https://api.openai.com/v1/responses"
            assert payload["text"]["format"]["strict"] is True
            assert payload["text"]["format"]["type"] == "json_schema"
            assert payload["store"] is False
            assert payload["max_output_tokens"] == 2048
            assert request.headers["authorization"] == "Bearer test-openai-key-not-a-real-secret"
        else:
            assert str(request.url) == "https://api.anthropic.com/v1/messages"
            assert payload["output_config"]["format"]["type"] == "json_schema"
            assert payload["max_tokens"] == 2048
            assert request.headers["anthropic-version"] == "2023-06-01"
            assert "anthropic-beta" not in request.headers
        return httpx.Response(200, json=_reply(provider, PLAN))

    result = _run_proposal(handler, provider)
    assert len(calls) == 1
    assert result["plan"] == PLAN
    assert result["provider"] == provider
    expected_cost = 0.0015 if provider == "openai" else 0.00175
    assert result["usage"]["estimated_cost_usd"] == pytest.approx(expected_cost)


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_summarize_research_is_advisory(provider):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_reply(provider, SUMMARY)))) as client:
            return await summarize_research({"gate": {"decision": "observe"}}, provider, budget_usd=1, client=client)
    result = asyncio.run(run())
    assert result["summary"] == SUMMARY["summary"]
    assert result["recommendation"] == "continue_observation"
    assert "order" not in result


@pytest.mark.parametrize("mutation", [
    lambda p: p["candidates"][0].update(kind="python", code="print('forbidden')"),
    lambda p: p["candidates"][0].update(fast_window=100, slow_window=20),
    lambda p: p["candidates"][0].update(fast_window="20"),
    lambda p: p.update(candidates=p["candidates"] * 9),
    lambda p: p.update(horizon_hours=1),
    lambda p: p.update(risks=[]),
    lambda p: p.update(execute_live=True),
])
def test_reject_model_code_invalid_bounds_and_extra_fields(mutation):
    invalid = copy.deepcopy(PLAN)
    mutation(invalid)
    with pytest.raises(AIError) as captured:
        _run_proposal(lambda _: httpx.Response(200, json=_reply("openai", invalid)))
    assert captured.value.code == "invalid_output"
    assert captured.value.may_be_charged is True
    assert captured.value.usage["input_tokens"] == 500


def test_reject_symbol_outside_dataset():
    invalid = copy.deepcopy(PLAN)
    invalid["candidates"][0]["symbol"] = "UNKNOWN"
    with pytest.raises(AIError, match="ajeno") as captured:
        _run_proposal(lambda _: httpx.Response(200, json=_reply("openai", invalid)))
    assert captured.value.usage is not None


def test_demo_symbol_with_underscore_is_supported():
    plan = copy.deepcopy(PLAN)
    plan["candidates"][0]["symbol"] = "DEMO_WORLD"

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=_reply("openai", plan)))) as client:
            return await propose_strategies("Probar datos sintéticos", {"symbols": ["DEMO_WORLD"]}, budget_usd=1, client=client)

    assert asyncio.run(run())["plan"]["candidates"][0]["symbol"] == "DEMO_WORLD"


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
@pytest.mark.parametrize("reason", ["refusal", "max_tokens"])
def test_refusals_and_truncations_never_accepted(provider, reason):
    reply = _reply(provider, PLAN)
    if provider == "openai":
        if reason == "refusal":
            reply["output"][0]["content"] = [{"type": "refusal", "refusal": "no"}]
        else:
            reply["status"] = "incomplete"
    else:
        reply["stop_reason"] = reason
    with pytest.raises(AIError):
        _run_proposal(lambda _: httpx.Response(200, json=reply), provider)


@pytest.mark.parametrize("budget", [0, -1, float("nan"), float("inf"), True, 0.00001])
def test_invalid_or_insufficient_budget_prevents_request(budget):
    def forbidden(_):
        pytest.fail("Budget check must run before sending any request")
    with pytest.raises(AIError):
        _run_proposal(forbidden, budget=budget)


def test_model_whitelist_prevents_unpriced_model_request():
    def forbidden(_):
        pytest.fail("Unpriced model must never be called")
    with pytest.raises(AIError, match="Modelo no admitido"):
        _run_proposal(forbidden, model="unknown-model")


def test_missing_key_is_not_simulated_ai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(AIError) as captured:
        _run_proposal(lambda _: pytest.fail("No API key"))
    assert captured.value.code == "missing_key"
    assert captured.value.may_be_charged is False


def test_status_does_not_leak_credentials():
    status = provider_status()
    assert all(provider["configured"] is True for provider in status)
    encoded = json.dumps(status)
    assert "test-openai-key" not in encoded
    assert "test-anthropic-key" not in encoded


def test_timeout_is_not_retried_and_retains_reservation():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("raw error with test-openai-key-not-a-real-secret", request=request)

    with pytest.raises(AIError) as captured:
        _run_proposal(handler)
    assert len(calls) == 1
    assert captured.value.code == "timeout"
    assert captured.value.reserved_cost_usd > 0
    assert captured.value.may_be_charged is True
    assert "test-openai-key" not in str(captured.value)


@pytest.mark.parametrize("status", [302, 401, 429, 500])
def test_http_failure_is_sanitized_and_redirects_not_followed(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": "test-openai-key-not-a-real-secret"}, headers={"Location": "https://attacker.invalid/"})

    with pytest.raises(AIError) as captured:
        _run_proposal(handler)
    assert len(calls) == 1
    assert "test-openai-key" not in str(captured.value)
    assert captured.value.code == "provider_http_error"


def test_missing_usage_cannot_hide_billing():
    reply = _reply("openai", PLAN)
    del reply["usage"]
    with pytest.raises(AIError) as captured:
        _run_proposal(lambda _: httpx.Response(200, json=reply))
    assert captured.value.code == "invalid_usage"
    assert captured.value.reserved_cost_usd > 0
    assert captured.value.usage is None


def test_reported_usage_above_reservation_fails_closed():
    reply = _reply("openai", PLAN)
    reply["usage"]["output_tokens"] = 10000
    with pytest.raises(AIError) as captured:
        _run_proposal(lambda _: httpx.Response(200, json=reply))
    assert captured.value.code == "usage_exceeded_reservation"
    assert captured.value.usage["output_tokens"] == 10000


def test_duplicate_json_properties_are_rejected():
    reply = _reply("openai", PLAN)
    raw = reply["output"][0]["content"][0]["text"]
    reply["output"][0]["content"][0]["text"] = raw[:-1] + ', "horizon_hours": 48}'
    with pytest.raises(AIError) as captured:
        _run_proposal(lambda _: httpx.Response(200, json=reply))
    assert captured.value.code == "invalid_output"


def test_utf8_byte_reservation_prevents_large_payload_before_send():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("oversized input must not be sent"))) as client:
            return await propose_strategies("Tendencia", {"symbols": ["SPY"], "context": "量" * 24_000}, budget_usd=10, client=client)
    with pytest.raises(AIError) as captured:
        asyncio.run(run())
    assert captured.value.code == "input_too_large"
    assert captured.value.may_be_charged is False


def _evidence():
    metrics = {"observations": 150, "trade_count": 12, "sharpe": 0.9, "max_drawdown": -0.08, "excess_return": 0.03}
    research = {
        "out_of_sample": {"metrics": metrics},
        "sensitivity": [{"cost_multiplier": m, "metrics": copy.deepcopy(metrics)} for m in (0.5, 1.0, 2.0)],
    }
    observation = {
        "elapsed_hours": 750, "new_sessions": 22, "source_kind": "observed", "reconciled": True,
        "forward_metrics": {"observations": 22, "total_return": 0.03, "max_drawdown": -0.04, "excess_return": 0.02},
    }
    return research, observation


def test_good_evidence_eligible_for_local_paper_only():
    research, observation = _evidence()
    result = evaluate_evidence(research, observation)
    assert result["decision"] == "eligible_paper"
    assert result["passed"] is True
    assert all(check["passed"] for check in result["checks"])
    assert any("dinero real" in text for text in result["limitations"])


def test_two_days_does_not_validate_daily_strategy():
    research, observation = _evidence()
    observation.update(elapsed_hours=49, new_sessions=2)
    result = evaluate_evidence(research, observation)
    assert result["decision"] == "observe"
    assert result["passed"] is False
    assert not next(c for c in result["checks"] if c["name"] == "new_forward_sessions")["passed"]


def test_synthetic_observations_cannot_promote():
    research, observation = _evidence()
    observation["source_kind"] = "synthetic"
    assert evaluate_evidence(research, observation)["decision"] == "observe"


@pytest.mark.parametrize("field,value", [("sharpe", float("nan")), ("excess_return", float("inf")), ("max_drawdown", -0.25), ("sharpe", None)])
def test_invalid_or_failed_metrics_rejected(field, value):
    research, observation = _evidence()
    research["out_of_sample"]["metrics"][field] = value
    result = evaluate_evidence(research, observation)
    assert result["decision"] == "rejected"
    json.dumps(result, allow_nan=False)


def test_failed_cost_sensitivity_rejects_positive_baseline():
    research, observation = _evidence()
    research["sensitivity"][-1]["metrics"]["excess_return"] = -0.01
    assert evaluate_evidence(research, observation)["decision"] == "rejected"


def test_missing_or_mismatched_stress_metrics_fail_closed():
    research, observation = _evidence()
    research["sensitivity"][-1]["metrics"]["observations"] = 120
    assert evaluate_evidence(research, observation)["decision"] == "rejected"
    research["sensitivity"] = []
    assert evaluate_evidence(research, observation)["decision"] == "rejected"


def test_elapsed_time_without_forward_performance_cannot_promote():
    research, observation = _evidence()
    del observation["forward_metrics"]
    assert evaluate_evidence(research, observation)["decision"] == "rejected"


@pytest.mark.parametrize("field,value", [("excess_return", -0.01), ("max_drawdown", -0.2), ("total_return", float("nan"))])
def test_forward_performance_must_pass_too(field, value):
    research, observation = _evidence()
    observation["forward_metrics"][field] = value
    assert evaluate_evidence(research, observation)["decision"] == "rejected"


@pytest.mark.parametrize("policy", [{"min_forward_sessions": 0}, {"requested_hours": -1}, {"max_drawdown": float("nan")}, {"min_sharpe": "0.5"}, {"min_trades": True}])
def test_invalid_policies_fail_closed(policy):
    research, observation = _evidence()
    result = evaluate_evidence(research, observation, policy)
    assert result["decision"] == "rejected"
    json.dumps(result, allow_nan=False)

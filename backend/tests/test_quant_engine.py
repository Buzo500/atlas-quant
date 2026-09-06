from copy import deepcopy
from datetime import date, timedelta
import json

import pytest

from atlas_quant.analytics import portfolio_snapshot
from atlas_quant.backtest import backtest, run_research


def bars(prices, symbol="ETF", opens=None):
    return [{"date": (date(2024, 1, 1) + timedelta(days=index)).isoformat(),
             "symbol": symbol, "open": (opens or prices)[index],
             "high": max(price, (opens or prices)[index]),
             "low": min(price, (opens or prices)[index]), "close": price,
             "volume": 10000, "currency": "EUR"} for index, price in enumerate(prices)]


def event(identifier, day, kind, **kwargs):
    return {"id": identifier, "date": f"2024-01-{day:02d}", "kind": kind,
            "currency": "EUR", **kwargs}


def free_backtest(data, strategy, initial_cash=1000):
    return backtest(data, strategy, initial_cash, commission_bps=0, slippage_bps=0, minimum_fee=0)


def test_ledger_cash_dividend_fee_and_cost_basis():
    ledger = [event("1", 1, "deposit", amount="1000"),
              event("2", 1, "buy", symbol="ETF", quantity="5", price="100", fee="2"),
              event("3", 2, "dividend", symbol="ETF", amount="10"),
              event("4", 2, "fee", amount="1")]
    result = portfolio_snapshot(ledger, bars([100, 110]))
    assert result["cash"] == 507
    assert result["nav"] == 1057
    assert result["pnl"] == 57
    assert result["positions"][0]["cost_basis"] == 502
    assert result["positions"][0]["unrealized_pnl"] == 48
    assert result["twr"] == pytest.approx(1057 / 998 - 1)


def test_contributions_do_not_create_returns_and_full_withdrawal_is_finite():
    ledger = [event("1", 1, "deposit", amount="100"),
              event("2", 2, "deposit", amount="200"),
              event("3", 3, "withdrawal", amount="300")]
    result = portfolio_snapshot(ledger, [])
    assert (result["nav"], result["pnl"], result["twr"]) == (0, 0, 0)
    json.dumps(result, allow_nan=False)


def test_split_preserves_cost_and_sale_releases_average_cost():
    ledger = [event("1", 1, "deposit", amount="1000"),
              event("2", 1, "buy", symbol="ETF", quantity="4", price="100", fee="4"),
              event("3", 2, "split", symbol="ETF", quantity="2"),
              event("4", 3, "sell", symbol="ETF", quantity="2", price="60", fee="1")]
    result = portfolio_snapshot(ledger, bars([100, 50, 60]))
    assert result["curve"][0]["nav"] == result["curve"][1]["nav"]
    assert result["positions"][0]["quantity"] == 6
    assert result["positions"][0]["cost_basis"] == 303
    assert result["nav"] == 1075
    assert result["cash"] == 715


def test_decimal_fractional_ledger_is_exact_before_serialization():
    ledger = [event("1", 1, "deposit", amount="0.3"),
              event("2", 1, "buy", symbol="ETF", quantity="3", price="0.1")]
    result = portfolio_snapshot(ledger, bars([0.1]))
    assert result["cash"] == 0
    assert result["nav"] == 0.3


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-1", None, True])
def test_ledger_rejects_nonfinite_or_negative_amounts(bad):
    with pytest.raises(ValueError):
        portfolio_snapshot([event("1", 1, "deposit", amount=bad)], [])


def test_reject_duplicate_short_insufficient_cash_and_fx():
    deposit = event("1", 1, "deposit", amount="100")
    with pytest.raises(ValueError, match="duplicado"):
        portfolio_snapshot([deposit, deposit], [])
    with pytest.raises(ValueError, match="cortos"):
        portfolio_snapshot([deposit, event("2", 1, "sell", symbol="ETF", quantity="1", price="10")], [])
    with pytest.raises(ValueError, match="insuficiente"):
        portfolio_snapshot([deposit, event("2", 1, "buy", symbol="ETF", quantity="20", price="10")], [])
    with pytest.raises(ValueError, match="EUR"):
        portfolio_snapshot([{**deposit, "currency": "USD"}], [])


def test_portfolio_rejects_future_price_and_marks_stale_prices():
    ledger = [event("1", 1, "deposit", amount="100"),
              event("2", 1, "buy", symbol="ETF", quantity="1", price="10")]
    with pytest.raises(ValueError, match="No hay cierre"):
        portfolio_snapshot(ledger, bars([10, 20])[1:])
    stale = portfolio_snapshot(ledger + [event("3", 2, "fee", amount="1")], bars([10]))
    assert stale["positions"][0]["price_date"] == "2024-01-01"
    assert any("últimos cierres" in warning for warning in stale["warnings"])


def test_empty_portfolio_has_no_infinities():
    result = portfolio_snapshot([], [])
    assert result["nav"] == 0
    assert result["curve"] == []
    json.dumps(result, allow_nan=False)


def test_buy_hold_executes_next_open_not_signal_close():
    result = free_backtest(bars([10, 100, 110], opens=[10, 20, 100]), {"kind": "buy_hold", "symbol": "ETF"})
    assert result["trades"][0] == {"date": "2024-01-02", "symbol": "ETF", "side": "buy", "quantity": 50, "price": 20.0, "fee": 0.0}
    assert result["curve"][0]["equity"] == 1000
    assert result["curve"][-1]["equity"] == 5500


def test_sma_is_causal_and_uses_previous_close():
    strategy = {"kind": "sma_cross", "symbol": "ETF", "fast_window": 1, "slow_window": 2}
    result = free_backtest(bars([10, 12, 1, 5], opens=[10, 12, 15, 2]), strategy)
    assert result["trades"][0]["date"] == "2024-01-03"
    assert result["trades"][0]["price"] == 15
    assert result["trades"][1]["date"] == "2024-01-04"
    assert result["trades"][1]["price"] == 2
    changed = free_backtest(bars([10, 12, 999, 999], opens=[10, 12, 15, 2]), strategy)
    assert result["trades"][0] == changed["trades"][0]


def test_cost_and_slippage_are_accounted_and_never_overdraw_cash():
    result = backtest(bars([100, 100, 100]), {"kind": "buy_hold", "symbol": "ETF"},
                      initial_cash=1000, commission_bps=10, slippage_bps=10, minimum_fee=2)
    assert result["trades"][0]["quantity"] == 9
    assert result["trades"][0]["price"] == pytest.approx(100.1)
    assert result["metrics"]["costs"] == pytest.approx(2.9)
    assert result["curve"][-1]["equity"] == pytest.approx(997.1)
    assert result["metrics"]["max_drawdown"] == pytest.approx(-0.0029)
    assert result["final_cash"] >= 0


def test_zero_volatility_sharpe_null_and_no_zero_volume_execution():
    data = bars([100, 100, 100])
    for bar in data:
        bar["volume"] = 0
    result = free_backtest(data, {"kind": "buy_hold", "symbol": "ETF"})
    assert result["trades"] == []
    assert result["metrics"]["sharpe"] is None
    json.dumps(result, allow_nan=False)


def test_temporal_momentum_and_unsupported_top_k():
    rule = {"kind": "momentum", "symbol": "ETF", "lookback": 2, "top_k": 1}
    result = free_backtest(bars([10, 11, 12, 13]), rule)
    assert result["trades"][0]["date"] == "2024-01-04"
    with pytest.raises(ValueError, match="top_k"):
        free_backtest(bars([10, 11]), {**rule, "top_k": 2})


def test_duplicate_bars_currency_and_invalid_configuration_rejected():
    data = bars([10, 11])
    rule = {"kind": "buy_hold", "symbol": "ETF"}
    with pytest.raises(ValueError, match="duplicada"):
        free_backtest(data + data[:1], rule)
    with pytest.raises(ValueError, match="EUR"):
        free_backtest([{**item, "currency": "USD"} for item in data], rule)
    with pytest.raises(ValueError, match="fast_window"):
        free_backtest(data, {"kind": "sma_cross", "symbol": "ETF", "fast_window": 10, "slow_window": 2})
    with pytest.raises(ValueError):
        backtest(data, rule, commission_bps=float("nan"))


def research_data():
    return bars([100 + index * 0.2 + (index % 9) * 0.1 for index in range(150)])


def test_holdout_does_not_select_candidate_and_partition_has_no_overlap():
    data = research_data()
    rules = [{"kind": "buy_hold", "symbol": "ETF"},
             {"kind": "sma_cross", "symbol": "ETF", "fast_window": 3, "slow_window": 8}]
    result = run_research(data, rules)
    changed = deepcopy(data)
    for index in range(120, 150):
        for key in ("open", "high", "low", "close"):
            changed[index][key] = 2000 - (index - 120) * 60
    alternative = run_research(changed, rules)
    assert result["candidate_results"] == alternative["candidate_results"]
    assert result["selected_strategy"] == alternative["selected_strategy"]
    assert result["data_hash"] != alternative["data_hash"]
    assert result["train_period"]["observations"] == 90
    assert result["validation_period"]["observations"] == 30
    assert result["test_period"]["observations"] == 30
    assert result["train_period"]["end"] < result["validation_period"]["start"]
    assert result["validation_period"]["end"] < result["test_period"]["start"]
    assert result["out_of_sample"]["metrics"] != alternative["out_of_sample"]["metrics"]
    assert all(item["period"] == "test" for item in result["sensitivity"])
    json.dumps(result, allow_nan=False)


def test_holdout_has_prior_history_warmup_without_reusing_prior_positions():
    data = bars([100 + index for index in range(150)])
    rule = {"kind": "sma_cross", "symbol": "ETF", "fast_window": 2, "slow_window": 100}
    result = run_research(data, [rule], initial_cash=10000, commission_bps=0, slippage_bps=0, minimum_fee=0)
    assert result["out_of_sample"]["trades"][0]["date"] == data[120]["date"]
    assert result["out_of_sample"]["trades"][0]["quantity"] == 45


def test_research_aligns_actual_dates_without_forward_fill():
    first = research_data()
    second = [{**bar, "symbol": "OTHER"} for bar in first[1:]]
    result = run_research(first + second, [{"kind": "buy_hold", "symbol": "ETF"}, {"kind": "buy_hold", "symbol": "OTHER"}])
    assert result["train_period"]["start"] == first[1]["date"]
    assert sum(result[key]["observations"] for key in ("train_period", "validation_period", "test_period")) == 149
    assert any("calendario común" in warning for warning in result["warnings"])


def test_research_insufficient_history_and_duplicate_candidates_rejected():
    rule = {"kind": "buy_hold", "symbol": "ETF"}
    with pytest.raises(ValueError, match="100"):
        run_research(bars([10] * 99), [rule])
    with pytest.raises(ValueError, match="duplicadas"):
        run_research(research_data(), [rule, rule])


def test_forward_evaluation_uses_previous_history_and_fresh_capital():
    data = bars([100 + index for index in range(150)])
    strategy = {"kind": "sma_cross", "symbol": "ETF", "fast_window": 2, "slow_window": 100}
    result = backtest(data, strategy, 1000, commission_bps=0, slippage_bps=0, minimum_fee=0,
                      evaluation_start=data[120]["date"])
    assert len(result["curve"]) == 30
    assert result["trades"][0]["date"] == data[120]["date"]
    assert result["trades"][0]["quantity"] == 4
    assert result["curve"][0]["equity"] == 1000


def test_forward_start_moves_to_next_observed_session_and_rejects_missing_future():
    data = bars([100, 101, 102, 103])
    rule = {"kind": "buy_hold", "symbol": "ETF"}
    result = backtest([data[0], *data[2:]], rule, evaluation_start="2024-01-02")
    assert result["curve"][0]["date"] == "2024-01-03"
    assert any("primera barra" in warning for warning in result["warnings"])
    with pytest.raises(ValueError, match="dos barras"):
        backtest(data, rule, evaluation_start="2025-01-01")


@pytest.mark.parametrize("weight,expected_quantity,expected_return", [(0.25, 25, 0.025), (0.5, 50, 0.05)])
def test_entry_weight_and_benchmark_share_the_same_exposure_budget(weight, expected_quantity, expected_return):
    result = backtest(bars([100, 100, 110]), {"kind": "buy_hold", "symbol": "ETF"},
                      initial_cash=10000, commission_bps=0, slippage_bps=0,
                      minimum_fee=0, max_position_weight=weight)
    assert result["trades"][0]["quantity"] == expected_quantity
    assert result["metrics"]["total_return"] == pytest.approx(expected_return)
    assert result["metrics"]["benchmark_return"] == pytest.approx(expected_return)
    assert result["metrics"]["excess_return"] == 0
    assert result["max_position_weight"] == weight


@pytest.mark.parametrize("weight", [0.25, 0.5])
@pytest.mark.parametrize("commission,minimum_fee", [(0, 2), (100, 0)])
def test_sizing_matches_paper_after_costs_and_slippage(weight, commission, minimum_fee):
    from atlas_quant.paper import advance_paper, new_account

    data = bars([100, 100, 110])
    rule = {"kind": "buy_hold", "symbol": "ETF"}
    kwargs = {"max_position_weight": weight, "commission_bps": commission,
              "slippage_bps": 10, "minimum_fee": minimum_fee}
    result = backtest(data, rule, initial_cash=10000, **kwargs)
    paper = advance_paper(new_account(10000, started_at_date="2023-12-31"),
                          data, rule, enabled=True, **kwargs)
    assert result["trades"][0]["quantity"] == paper["fills"][0]["quantity"]
    assert result["final_cash"] == paper["cash"]
    assert result["curve"][-1]["equity"] == paper["equity"]
    assert paper["fills"][0]["position_weight_at_fill"] <= weight


@pytest.mark.parametrize("weight", [0, -0.1, 1.01, float("nan"), True])
def test_invalid_position_weights_fail_closed(weight):
    rule = {"kind": "buy_hold", "symbol": "ETF"}
    with pytest.raises(ValueError, match="max_position_weight"):
        backtest(bars([100, 110]), rule, max_position_weight=weight)
    with pytest.raises(ValueError, match="max_position_weight"):
        run_research(research_data(), [rule], max_position_weight=weight)


def test_research_applies_frozen_weight_to_validation_holdout_and_stress():
    data = research_data()
    rule = {"kind": "buy_hold", "symbol": "ETF"}
    common = {"initial_cash": 10000, "commission_bps": 10, "slippage_bps": 5,
              "minimum_fee": 2, "max_position_weight": 0.25}
    result = run_research(data, [rule], **common)
    validation = backtest(data[:120], rule, evaluation_start=data[90]["date"], **common)
    assert result["candidate_results"][0]["validation_metrics"] == validation["metrics"]
    holdout = backtest(data, rule, evaluation_start=data[120]["date"], **common)
    assert result["out_of_sample"]["metrics"] == holdout["metrics"]
    doubled = {**common, "commission_bps": 20, "slippage_bps": 10, "minimum_fee": 4}
    stressed = backtest(data, rule, evaluation_start=data[120]["date"], **doubled)
    assert result["sensitivity"][-1]["metrics"] == stressed["metrics"]
    assert result["max_position_weight"] == 0.25
    assert result["full_result"]["max_position_weight"] == 0.25

import copy
import json
import unittest

from atlas_quant.paper import advance_paper, new_account


RULE = {"kind": "buy_hold", "symbol": "DEMO_WORLD"}


def bar(day, opening=100, close=100, volume=10000):
    return {"date": f"2026-01-{day:02d}", "symbol": "DEMO_WORLD", "open": opening,
            "high": max(opening, close) + 1, "low": min(opening, close) - 1,
            "close": close, "volume": volume, "currency": "EUR"}


class PaperTests(unittest.TestCase):
    def test_close_signal_fills_only_at_strictly_later_open(self):
        initial = new_account(started_at_date="2026-01-01")
        first = advance_paper(initial, [bar(2, 100, 150)], RULE, enabled=True, minimum_fee=0, commission_bps=0, slippage_bps=0)
        self.assertEqual(first["fills"], [])
        self.assertEqual(first["orders"][0]["status"], "pending")
        second = advance_paper(first, [bar(5, 200, 300)], RULE, enabled=True, minimum_fee=0, commission_bps=0, slippage_bps=0)
        self.assertEqual(len(second["fills"]), 1)
        fill = second["fills"][0]
        self.assertEqual((fill["signal_date"], fill["date"], fill["price"]), ("2026-01-02", "2026-01-05", 200))
        self.assertEqual(fill["quantity"], 12)
        self.assertEqual(second["cash"], 7600)
        self.assertEqual(second["equity"], 11200)
        self.assertEqual(initial["orders"], [])
        self.assertEqual(first["orders"][0]["status"], "pending")

    def test_repeated_data_is_idempotent_and_json_roundtrip_safe(self):
        bars = [bar(2), bar(5), bar(6)]
        account = new_account(started_at_date="2026-01-01")
        once = advance_paper(account, bars, RULE, enabled=True)
        twice = advance_paper(json.loads(json.dumps(once)), bars, RULE, enabled=True)
        self.assertEqual(once, twice)
        self.assertEqual(len(twice["fills"]), 1)
        self.assertEqual(len(twice["equity_curve"]), 3)

    def test_disabled_cancels_pending_and_does_not_replay_missed_sessions(self):
        account = advance_paper(new_account(started_at_date="2026-01-01"), [bar(2)], RULE, enabled=True)
        stopped = advance_paper(account, [bar(5)], RULE, enabled=False)
        self.assertEqual(stopped["orders"][0]["status"], "cancelled")
        self.assertEqual(stopped["fills"], [])
        self.assertEqual(stopped["last_processed_date"], "2026-01-05")
        resumed = advance_paper(stopped, [bar(6)], RULE, enabled=True)
        self.assertEqual(resumed["fills"], [])
        self.assertEqual(resumed["orders"][-1]["signal_date"], "2026-01-06")
        filled = advance_paper(resumed, [bar(7)], RULE, enabled=True)
        self.assertEqual(filled["fills"][0]["date"], "2026-01-07")

    def test_disabled_can_cancel_without_any_new_data(self):
        account = advance_paper(new_account(started_at_date="2026-01-01"), [bar(2)], RULE, enabled=True)
        stopped = advance_paper(account, [], RULE, enabled=False)
        self.assertEqual(stopped["orders"][0]["status"], "cancelled")
        self.assertEqual(stopped["fills"], [])

    def test_cash_and_position_caps_include_fees_and_slippage(self):
        for weight in (0.01, 0.25, 1):
            for cost in (0, 5, 1000):
                with self.subTest(weight=weight, cost=cost):
                    result = advance_paper(new_account(1000, started_at_date="2026-01-01"), [bar(2, 7, 7), bar(5, 9, 9)], RULE, enabled=True, max_position_weight=weight, commission_bps=cost, slippage_bps=cost, minimum_fee=2)
                    self.assertGreaterEqual(result["cash"], 0)
                    for fill in result["fills"]:
                        self.assertGreater(fill["quantity"], 0)
                        self.assertEqual(fill["quantity"], int(fill["quantity"]))
                        self.assertLessEqual(fill["position_weight_at_fill"], weight + 1e-12)

    def test_unaffordable_order_is_rejected_and_never_leverages(self):
        result = advance_paper(new_account(1, started_at_date="2026-01-01"), [bar(2), bar(5)], RULE, enabled=True)
        self.assertEqual(result["fills"], [])
        self.assertEqual(result["orders"][0]["status"], "rejected")
        self.assertEqual(result["cash"], 1)
        self.assertEqual(result["positions"], {})

    def test_invalid_quotes_fail_atomically(self):
        original = new_account(started_at_date="2026-01-01")
        saved = copy.deepcopy(original)
        invalids = [dict(bar(5), open=float("nan")), dict(bar(5), low=101), dict(bar(5), volume=-1), dict(bar(5), currency="USD"), dict(bar(5), close=0)]
        missing = bar(5)
        del missing["volume"]
        invalids.append(missing)
        for invalid in invalids:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                advance_paper(original, [bar(2), invalid], RULE, enabled=True)
            self.assertEqual(original, saved)
        with self.assertRaises(ValueError):
            advance_paper(original, [bar(2), bar(2)], RULE, enabled=True)

    def test_cutoff_history_warms_indicators_but_never_creates_old_orders(self):
        rule = {"kind": "sma_cross", "symbol": "DEMO_WORLD", "fast_window": 1, "slow_window": 3}
        result = advance_paper(new_account(started_at_date="2026-01-05"), [bar(2, 100, 100), bar(5, 101, 101), bar(6, 102, 102)], rule, enabled=True)
        self.assertEqual(len(result["orders"]), 1)
        self.assertEqual(result["orders"][0]["signal_date"], "2026-01-06")
        self.assertEqual(result["fills"], [])
        self.assertEqual(len(result["equity_curve"]), 1)

    def test_momentum_exits_at_next_open_without_shorting(self):
        rule = {"kind": "momentum", "symbol": "DEMO_WORLD", "lookback": 1}
        result = advance_paper(new_account(started_at_date="2026-01-01"), [bar(2, 100, 100), bar(5, 110, 110), bar(6, 120, 90), bar(7, 80, 80)], rule, enabled=True, minimum_fee=0, commission_bps=0, slippage_bps=0)
        self.assertEqual([fill["side"] for fill in result["fills"]], ["buy", "sell"])
        self.assertEqual([fill["date"] for fill in result["fills"]], ["2026-01-06", "2026-01-07"])
        self.assertEqual(result["positions"], {})
        self.assertEqual(result["cash"], 9200)

    def test_historical_revision_and_strategy_mutation_fail_closed(self):
        account = advance_paper(new_account(started_at_date="2026-01-01"), [bar(2), bar(5)], RULE, enabled=True)
        with self.assertRaisesRegex(ValueError, "cambió"):
            advance_paper(account, [bar(2, 101, 101)], RULE, enabled=True)
        with self.assertRaisesRegex(ValueError, "antiguas"):
            advance_paper(account, [bar(3)], RULE, enabled=True)
        with self.assertRaisesRegex(ValueError, "congelada"):
            advance_paper(account, [bar(6)], {"kind": "momentum", "symbol": "DEMO_WORLD", "lookback": 1}, enabled=True)

    def test_zero_volume_blocks_fill(self):
        result = advance_paper(new_account(started_at_date="2026-01-01"), [bar(2), bar(5, volume=0)], RULE, enabled=True)
        self.assertEqual(result["fills"], [])
        self.assertEqual(result["orders"][0]["reason"], "zero_volume")

    def test_bad_limits_and_corrupt_cash_fail_closed(self):
        account = new_account(started_at_date="2026-01-01")
        for kwargs in ({"max_position_weight": 1.1}, {"max_position_weight": 0}, {"commission_bps": -1}, {"slippage_bps": float("inf")}, {"minimum_fee": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                advance_paper(account, [bar(2)], RULE, enabled=True, **kwargs)
        account["cash"] = -1
        with self.assertRaises(ValueError):
            advance_paper(account, [bar(2)], RULE, enabled=True)


if __name__ == "__main__":
    unittest.main()

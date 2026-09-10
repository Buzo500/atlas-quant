"""Provider-contract tests use no network and do not require yfinance/pandas."""

import threading
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from atlas_quant import feed


def row(close=100, **changes):
    values = {"Open": close, "High": close + 1, "Low": close - 1, "Close": close, "Volume": 10000, "Dividends": 0, "Stock Splits": 0}
    values.update(changes)
    return values


class Frame:
    def __init__(self, rows, columns=None):
        self.rows = rows
        self.columns = list(columns if columns is not None else (rows[0][1].keys() if rows else feed._REQUIRED_COLUMNS))

    def iterrows(self):
        return iter(self.rows)


class FeedTests(unittest.TestCase):
    def test_provider_cache_is_local_and_configured_before_first_ticker(self):
        provider = SimpleNamespace(set_tz_cache_location=Mock())
        with tempfile.TemporaryDirectory() as directory, patch.dict(feed.os.environ, {"ATLAS_DATA_DIR": directory}), patch.object(feed, "_PROVIDER_CACHE", None), patch.object(feed.importlib, "import_module", return_value=provider):
            self.assertIs(feed._load_provider(), provider)
            self.assertIs(feed._load_provider(), provider)
            target = feed.Path(directory).resolve() / "cache" / "yfinance"
            self.assertTrue(target.is_dir())
            provider.set_tz_cache_location.assert_called_once_with(str(target))
            with patch.dict(feed.os.environ, {"ATLAS_DATA_DIR": str(target / "other")}), self.assertRaisesRegex(feed.FeedError, "Reinicia"):
                feed._load_provider()

    def setUp(self):
        self.today = patch.object(feed, "_today_utc", return_value=date(2026, 9, 5))
        self.today.start()
        self.addCleanup(self.today.stop)
        self.metadata = {"currency": "EUR", "symbol": "EXAMPLE.DE", "instrumentType": "ETF", "exchangeName": "GER", "exchangeTimezoneName": "Europe/Berlin"}

    def fetch(self, frame=None, metadata=None, **kwargs):
        frame = frame if frame is not None else Frame([("2026-09-03", row()), ("2026-09-04", row(101))])
        with patch.object(feed, "_bounded_snapshot", return_value=(frame, metadata if metadata is not None else self.metadata, "test")) as snapshot:
            result = feed.fetch_daily("example.de", "2026-09-01", **kwargs)
        return result, snapshot

    def test_eur_snapshot_has_provenance_and_raw_prices(self):
        result, snapshot = self.fetch()
        self.assertEqual(result["source_kind"], "observed")
        self.assertEqual(result["bars"][0]["close"], 100)
        self.assertEqual(result["bars"][0]["currency"], "EUR")
        self.assertFalse(result["source_metadata"]["auto_adjust"])
        self.assertFalse(result["source_metadata"]["is_realtime"])
        self.assertTrue(result["source_metadata"]["currency_verified"])
        self.assertEqual(result["corporate_actions"], [])
        snapshot.assert_called_once_with("EXAMPLE.DE", "2026-09-01", "2026-09-05")

    def test_today_future_and_out_of_range_rows_are_excluded(self):
        frame = Frame([("2026-08-31", row()), ("2026-09-04", row()), ("2026-09-05", row()), ("2026-09-06", row())])
        result, snapshot = self.fetch(frame, end="2026-09-10")
        self.assertEqual([bar["date"] for bar in result["bars"]], ["2026-09-04"])
        self.assertEqual(result["source_metadata"]["end_exclusive"], "2026-09-05")
        self.assertTrue(any("3 filas" in warning for warning in result["warnings"]))

    def test_exchange_session_date_is_not_shifted_back_by_utc_conversion(self):
        stamp = datetime(2026, 9, 4, 0, 0, tzinfo=timezone(timedelta(hours=2)))
        result, _ = self.fetch(Frame([(stamp, row())]))
        self.assertEqual(result["bars"][0]["date"], "2026-09-04")

    def test_currency_is_verified_not_inferred_from_suffix(self):
        for currency in ("USD", "GBp", None, "eur"):
            with self.subTest(currency=currency), self.assertRaisesRegex(feed.FeedError, "moneda confirmada"):
                self.fetch(metadata={**self.metadata, "currency": currency})
        with self.assertRaises(feed.FeedError):
            self.fetch(metadata={**self.metadata, "instrumentType": "CRYPTOCURRENCY"})
        with self.assertRaises(feed.FeedError):
            self.fetch(metadata={**self.metadata, "symbol": "OTHER.DE"})

    def test_actions_are_returned_without_price_or_ledger_adjustment(self):
        frame = Frame([("2026-09-03", row(**{"Dividends": 1.5, "Stock Splits": 2, "Capital Gains": 0.25})), ("2026-09-04", row(50, **{"Capital Gains": 0}))])
        result, _ = self.fetch(frame)
        self.assertEqual({action["kind"] for action in result["corporate_actions"]}, {"dividend", "split", "capital_gain"})
        self.assertEqual(result["bars"][0]["close"], 100)
        self.assertEqual(result["bars"][1]["close"], 50)
        self.assertTrue(all(not action["applied_to_ledger"] for action in result["corporate_actions"]))
        self.assertTrue(any("bloquea" in warning for warning in result["warnings"]))

    def test_bad_dates_and_tickers_do_not_contact_provider(self):
        with patch.object(feed, "_bounded_snapshot") as download:
            for symbol in ("AAPL,MSFT", "https://host", "../../file", "=SUM(A1)", "A" * 26, "", "^INDEX"):
                with self.subTest(symbol=symbol), self.assertRaises(feed.FeedError):
                    feed.fetch_daily(symbol, "2026-09-01")
            for start, end in (("2026-02-30", None), ("2026-09-05", None), ("2025-01-01", "2024-01-01"), ("2010-01-01", "2026-01-01"), ("01/01/2026", None)):
                with self.subTest(start=start, end=end), self.assertRaises(feed.FeedError):
                    feed.fetch_daily("EXAMPLE.DE", start, end)
            download.assert_not_called()

    def test_missing_nan_inconsistent_duplicate_and_empty_responses_fail_closed(self):
        frames = [
            Frame([]),
            Frame([("2026-09-04", row())], columns=["Open", "High", "Low", "Close", "Volume"]),
            Frame([("2026-09-04", row(Close=float("nan")))]),
            Frame([("2026-09-04", row(High=90))]),
            Frame([("2026-09-04", row(Volume=-1))]),
            Frame([("2026-09-04", row()), ("2026-09-04", row())]),
        ]
        for frame in frames:
            with self.subTest(frame=frame.rows), self.assertRaises(feed.FeedError):
                self.fetch(frame)

    def test_fully_missing_zero_volume_rows_are_reported_as_gaps_and_keep_actions(self):
        empty = row(Open=float("nan"), High=float("nan"), Low=float("nan"), Close=float("nan"), Volume=0, Dividends=1.25)
        result, _ = self.fetch(Frame([("2026-09-02", empty), ("2026-09-03", row()), ("2026-09-04", row(101))]))
        self.assertEqual([bar["date"] for bar in result["bars"]], ["2026-09-03", "2026-09-04"])
        self.assertEqual(result["source_metadata"]["excluded_empty_quote_rows"], 1)
        self.assertEqual(result["source_metadata"]["excluded_empty_quote_dates"], ["2026-09-02"])
        self.assertEqual(result["source_metadata"]["received_rows"], 3)
        self.assertEqual(result["source_metadata"]["accepted_rows"], 2)
        self.assertEqual(result["corporate_actions"][0]["date"], "2026-09-02")
        self.assertEqual(result["corporate_actions"][0]["value"], 1.25)
        self.assertTrue(any("huecos sin precios" in warning for warning in result["warnings"]))

    def test_partial_quotes_and_missing_quotes_with_volume_are_never_excluded(self):
        cases = [
            row(Close=float("nan"), Volume=0),
            row(Close=float("nan"), Volume=100),
            row(Open=float("nan"), High=float("nan"), Low=float("nan"), Close=float("nan"), Volume=1),
            row(Open=0, High=0, Low=0, Close=0, Volume=0),
            row(Open=float("nan"), High=float("nan"), Low=float("nan"), Close=float("nan"), Volume=float("nan")),
            row(Open=float("nan"), High=float("nan"), Low=float("nan"), Close=float("nan"), Volume=0, Dividends=float("nan")),
        ]
        for invalid in cases:
            with self.subTest(invalid=invalid), self.assertRaises(feed.FeedError):
                self.fetch(Frame([("2026-09-03", row()), ("2026-09-04", invalid)]))

    def test_an_empty_quote_row_cannot_hide_a_duplicate_session(self):
        empty = row(Open=None, High=None, Low=None, Close=None, Volume=0)
        with self.assertRaisesRegex(feed.FeedError, "duplicada"):
            self.fetch(Frame([("2026-09-04", empty), ("2026-09-04", row())]))

    def test_real_adapter_requests_explicit_parameters_and_only_base_metadata(self):
        ticker = Mock()
        ticker.history.return_value = Frame([("2026-09-04", row())])
        ticker.get_history_metadata.return_value = self.metadata
        provider = SimpleNamespace(Ticker=Mock(return_value=ticker), __version__="test")
        with patch.object(feed, "_load_provider", return_value=provider):
            frame, metadata, version = feed._call_provider("EXAMPLE.DE", "2026-09-01", "2026-09-05")
        provider.Ticker.assert_called_once_with("EXAMPLE.DE")
        kwargs = ticker.history.call_args.kwargs
        self.assertEqual(kwargs["interval"], "1d")
        self.assertEqual(kwargs["timeout"], 10)
        self.assertFalse(kwargs["auto_adjust"])
        self.assertFalse(kwargs["repair"])
        self.assertTrue(kwargs["actions"])
        self.assertTrue(kwargs["keepna"])
        self.assertTrue(kwargs["raise_errors"])
        self.assertEqual(metadata["currency"], "EUR")

    def test_missing_optional_dependency_and_provider_errors_are_clear(self):
        with patch.object(feed.importlib, "import_module", side_effect=ModuleNotFoundError("yfinance")):
            with self.assertRaisesRegex(feed.FeedError, "dependencia opcional yfinance"):
                feed._load_provider()
        with patch.object(feed, "_call_provider", side_effect=TimeoutError("network")):
            with self.assertRaisesRegex(feed.FeedError, "TimeoutError"):
                feed._bounded_snapshot("EXAMPLE.DE", "2026-09-01", "2026-09-05")

    def test_outer_deadline_discards_late_results_and_limits_workers(self):
        release = threading.Event()
        completed = threading.Event()

        def blocked(*args):
            release.wait(timeout=1)
            completed.set()
            return Frame([]), self.metadata, "test"

        slots = threading.BoundedSemaphore(1)
        with patch.object(feed, "_FETCH_SLOTS", slots), patch.object(feed, "FETCH_DEADLINE_SECONDS", 0.01), patch.object(feed, "_call_provider", side_effect=blocked):
            try:
                with self.assertRaisesRegex(feed.FeedError, "respuesta tardía"):
                    feed._bounded_snapshot("EXAMPLE.DE", "2026-09-01", "2026-09-05")
                with self.assertRaisesRegex(feed.FeedError, "descargas en curso"):
                    feed._bounded_snapshot("EXAMPLE.DE", "2026-09-01", "2026-09-05")
            finally:
                release.set()
                self.assertTrue(completed.wait(timeout=1))


if __name__ == "__main__":
    unittest.main()

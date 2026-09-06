"""Data-contract tests: corrupt inputs must fail before they reach a ledger."""

import csv
import io
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from atlas_quant.data import (
    DataValidationError,
    build_provenance_manifest,
    demo_dataset,
    ledger_csv_template,
    parse_ledger_csv,
    parse_prices_csv,
    price_csv_template,
)


class PriceCsvTests(unittest.TestCase):
    def test_prices_are_sorted_normalized_and_currency_defaults_to_eur(self):
        rows = parse_prices_csv(
            "\ufeff date ; symbol ; open ; high ; low ; close ; volume\n"
            "2026-01-06;demo_world;101;103;100;102;0\n"
            "2026-01-05;DEMO_WORLD;100;102;99;101;100\n"
        )
        self.assertEqual(rows[0]["date"], "2026-01-05")
        self.assertEqual(rows[0]["symbol"], "DEMO_WORLD")
        self.assertEqual(rows[0]["currency"], "EUR")
        self.assertEqual(rows[1]["volume"], 0)

    def test_duplicate_bars_are_never_silently_deduplicated(self):
        template = price_csv_template()
        with self.assertRaisesRegex(DataValidationError, "duplicada"):
            parse_prices_csv(template + template.splitlines()[1] + "\n")

    def test_missing_fields_empty_and_single_bar_fail(self):
        for text in ("", "date,symbol,close\n2026-01-05,DEMO_WORLD,10\n", "\n".join(price_csv_template().splitlines()[:2])):
            with self.subTest(text=text), self.assertRaises(DataValidationError):
                parse_prices_csv(text)

    def test_ambiguous_decimal_and_nonfinite_values_fail(self):
        for value in ("NaN", "Infinity", "-Infinity", "1e2", "1,25", "1 000", "", "=1+2", "１２"):
            text = "date;symbol;open;high;low;close;volume\n"
            text += f"2026-01-05;DEMO_WORLD;{value};102;99;101;100\n"
            text += "2026-01-06;DEMO_WORLD;101;103;100;102;100\n"
            with self.subTest(value=value), self.assertRaises(DataValidationError):
                parse_prices_csv(text)

    def test_zero_negative_incoherent_prices_negative_volume_and_fx_fail(self):
        template = price_csv_template()
        mutations = (
            template.replace(",100,102,99,101,", ",0,102,99,101,"),
            template.replace(",100,102,99,101,", ",-1,102,99,101,"),
            template.replace(",100,102,99,101,", ",100,98,99,101,"),
            template.replace(",100,102,99,101,", ",100,102,101,101,"),
            template.replace(",100000,", ",-1,"),
            template.replace("EUR", "USD"),
        )
        for text in mutations:
            with self.subTest(text=text), self.assertRaises(DataValidationError):
                parse_prices_csv(text)

    def test_dates_must_be_valid_iso_and_header_must_be_unambiguous(self):
        template = price_csv_template()
        for text in (
            template.replace("2026-01-05", "2026-02-30"),
            template.replace("2026-01-05", "05/01/2026"),
            template.replace("2026-01-05", "20260105"),
            template.replace("open,high", "close,high"),
            template.replace("volume,currency", "volum,currency"),
            template.replace(",EUR\n", ",EUR,extra\n", 1),
            template.replace(",EUR\n", "\n", 1),
            template + '"unterminated\n',
        ):
            with self.subTest(text=text), self.assertRaises(DataValidationError):
                parse_prices_csv(text)

    def test_binary_invalid_unicode_and_formula_symbols_rejected(self):
        for text in (b"\xff\xfe", price_csv_template() + "\ud800", price_csv_template().replace("DEMO_WORLD", "=SUM(A1:A2)")):
            with self.subTest(text=repr(text)), self.assertRaises(DataValidationError):
                parse_prices_csv(text)


class LedgerCsvTests(unittest.TestCase):
    def test_templates_import_and_trade_amount_is_exact_gross(self):
        events = parse_ledger_csv(ledger_csv_template())
        self.assertEqual(events[0]["amount"], "10000")
        self.assertEqual(events[1]["amount"], "1010")
        self.assertEqual(events[1]["fee"], "1")
        self.assertIsInstance(events[1]["quantity"], str)
        text = "date,kind,symbol,quantity,price,fee\n2026-01-05,buy,DEMO_WORLD,0.1,0.2,0.001\n"
        event = parse_ledger_csv(text)[0]
        self.assertEqual(event["amount"], "0.02")
        self.assertEqual(event["currency"], "EUR")

    def test_trade_multiplication_does_not_use_decimal_default_precision(self):
        text = "date,kind,symbol,quantity,price\n2026-01-05,buy,DEMO_WORLD,12345678901234567890123456789,9\n"
        self.assertEqual(parse_ledger_csv(text)[0]["amount"], "111111110111111111011111111101")

    def test_stable_ids_ignore_harmless_formatting_and_identical_rows_deduplicate(self):
        first = parse_ledger_csv("date,kind,amount\n2026-01-05,deposit,100.00\n")[0]
        second = parse_ledger_csv("amount;kind;date;currency\n100;DEPOSIT;2026-01-05;EUR\n")[0]
        self.assertEqual(first, second)
        deduplicated = parse_ledger_csv("date,kind,amount\n2026-01-05,deposit,100\n2026-01-05,deposit,100.0\n")
        self.assertEqual(len(deduplicated), 1)

    def test_external_ids_support_identical_distinct_events_and_reject_collisions(self):
        text = "id,date,kind,amount\na,2026-01-05,deposit,100\nb,2026-01-05,deposit,100\n"
        self.assertEqual(len(parse_ledger_csv(text)), 2)
        self.assertEqual(len(parse_ledger_csv(text + "a,2026-01-05,deposit,100.0\n")), 2)
        with self.assertRaisesRegex(DataValidationError, "contenido diferente"):
            parse_ledger_csv(text + "a,2026-01-05,deposit,101\n")

    def test_supported_events_preserve_same_day_causal_order(self):
        text = (
            "date,kind,symbol,quantity,price,amount,fee\n"
            "2026-01-06,withdrawal,,,,50,\n"
            "2026-01-05,deposit,,,,1000,\n"
            "2026-01-05,buy,DEMO_WORLD,1,100,,1\n"
            "2026-01-05,split,DEMO_WORLD,2,,,,\n"
        )
        # Build the split row with the correct seven-column schema.
        text = text.replace("DEMO_WORLD,2,,,,", "DEMO_WORLD,2,,,")
        text += "2026-01-05,dividend,DEMO_WORLD,,,2,\n2026-01-05,sell,DEMO_WORLD,1,51,,1\n2026-01-05,fee,,,,0.5,\n"
        events = parse_ledger_csv(text)
        self.assertEqual([event["kind"] for event in events], ["deposit", "buy", "split", "dividend", "sell", "fee", "withdrawal"])
        self.assertEqual(events[2]["quantity"], "2")

    def test_invalid_ledger_data_fails_atomically(self):
        header = "date,kind,symbol,quantity,price,amount,fee,currency\n"
        rows = (
            "2026-01-05,deposit,,,,-100,,EUR\n",
            "2026-01-05,deposit,DEMO_WORLD,,,100,,EUR\n",
            "2026-01-05,deposit,,,,100,1,EUR\n",
            "2026-01-05,deposit,,,,,,EUR\n",
            "2026-01-05,buy,DEMO_WORLD,0,100,,,EUR\n",
            "2026-01-05,buy,,1,100,,,EUR\n",
            "2026-01-05,buy,DEMO_WORLD,1,100,99,,EUR\n",
            "2026-01-05,buy,DEMO_WORLD,1,100,,-1,EUR\n",
            "2026-01-05,sell,DEMO_WORLD,-1,100,,,EUR\n",
            "2026-01-05,split,DEMO_WORLD,0,,,,EUR\n",
            "2026-01-05,split,DEMO_WORLD,2,,1,,EUR\n",
            "2026-01-05,dividend,,,,1,,EUR\n",
            "2026-01-05,fee,,,,1,,USD\n",
            "2026-01-05,unknown,,,,1,,EUR\n",
        )
        for row in rows:
            with self.subTest(row=row), self.assertRaises(DataValidationError):
                parse_ledger_csv(header + "2026-01-04,deposit,,,,1000,,EUR\n" + row)
        with self.assertRaises(DataValidationError):
            parse_ledger_csv("date,kind\n")


class ProvenanceAndDemoTests(unittest.TestCase):
    def test_hash_is_reproducible_order_independent_and_content_sensitive(self):
        bars = parse_prices_csv(price_csv_template())
        one = build_provenance_manifest(bars, "test", "csv", "user file")
        two = build_provenance_manifest(list(reversed(bars)), "renamed", "csv", "another filename")
        self.assertEqual(one["sha256"], two["sha256"])
        self.assertEqual(one["counts_by_symbol"], {"DEMO_WORLD": 2})
        self.assertEqual(one["date_min"], "2026-01-05")
        self.assertEqual(one["date_max"], "2026-01-06")
        self.assertFalse(one["synthetic"])
        self.assertIsNotNone(datetime.fromisoformat(one["generated_at"]).tzinfo)
        bars[0]["close"] = 100.5
        changed = build_provenance_manifest(bars, "test", "csv", "user file")
        self.assertNotEqual(one["sha256"], changed["sha256"])

    def test_demo_is_explicitly_synthetic_and_roundtrips_through_validation(self):
        demo = demo_dataset()
        self.assertEqual(demo["source_kind"], "synthetic")
        self.assertTrue(demo["metadata"]["synthetic"])
        self.assertFalse(demo["metadata"]["is_live"])
        self.assertEqual(demo["metadata"]["row_count"], 3300)
        self.assertEqual(set(demo["metadata"]["symbols"]), {"DEMO_WORLD", "DEMO_EURO", "DEMO_BOND"})
        expected = datetime.now(timezone.utc).date()
        while expected.weekday() > 4:
            expected -= timedelta(days=1)
        self.assertEqual(demo["metadata"]["date_max"], expected.isoformat())
        self.assertTrue(all(datetime.fromisoformat(bar["date"]).weekday() < 5 for bar in demo["bars"]))
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=["date", "symbol", "open", "high", "low", "close", "volume", "currency"])
        writer.writeheader()
        writer.writerows(demo["bars"])
        self.assertEqual(parse_prices_csv(output.getvalue()), demo["bars"])
        deposits = sum(Decimal(event["amount"]) for event in demo["events"] if event["kind"] == "deposit")
        purchases = sum(Decimal(event["amount"]) + Decimal(event["fee"]) for event in demo["events"] if event["kind"] == "buy")
        self.assertGreater(deposits, purchases)
        self.assertEqual(demo["bars"], demo_dataset()["bars"])


if __name__ == "__main__":
    unittest.main()

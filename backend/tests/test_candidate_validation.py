"""Safety and comparison checks for the real Windows release walkthrough."""
from copy import deepcopy
import json
import sqlite3

import pytest

from validate_candidate import Assets, Walkthrough, clean_environment, require_demo_only, snapshot, stable_content


def demo_snapshot():
    return {"schema": 0, "records": {
        ("dataset", "d"): {"id": "d", "source_kind": "synthetic", "bars": [{"close": 100}]},
        ("experiment", "j"): {"id": "j", "status": "observing", "provider": "none", "budget_usd": 0,
                               "spent_usd": 0, "reserved_usd": 0, "auto_paper": False, "paper_account": None,
                               "research": {"selected_strategy": {"kind": "buy_hold"}}},
    }, "versions": []}


def test_environment_does_not_inherit_credentials_or_other_data_directory():
    env = clean_environment({"OpenAI_API_KEY": "secret", "ANTHROPIC_API_KEY": "secret",
                             "ATLAS_DATA_DIR": "other", "PYTHONPATH": "other", "PATH": "runtime"})
    assert env == {"PATH": "runtime", "PYTHONUTF8": "1"}


@pytest.mark.parametrize("change", [
    {"provider": "openai"}, {"budget_usd": 1}, {"spent_usd": 1}, {"reserved_usd": 1},
    {"auto_paper": True}, {"paper_account": {"cash": 100}},
])
def test_rejects_nonzero_or_paper_historical_experiment(change):
    value = demo_snapshot()
    value["records"][("experiment", "j")].update(change)
    with pytest.raises(RuntimeError, match="provider none"):
        require_demo_only(value)


def test_rejects_network_feed_in_historical_data():
    value = demo_snapshot()
    value["records"][("dataset", "d")]["feed"] = {"symbol": "REAL"}
    with pytest.raises(RuntimeError, match="fuente automática"):
        require_demo_only(value)


def test_financial_comparison_ignores_only_lifecycle_and_schema():
    before = demo_snapshot()
    after = deepcopy(before)
    after["schema"] = 1
    after["records"][("experiment", "j")].update(status="paused", execution_active=False,
                                                   observation={"elapsed_hours": 2})
    assert stable_content(before) == stable_content(after)
    after["records"][("experiment", "j")]["research"]["selected_strategy"]["kind"] = "sma_cross"
    assert stable_content(before) != stable_content(after)


def test_financial_comparison_detects_historical_version_change():
    before = demo_snapshot()
    after = deepcopy(before)
    after["versions"] = [("d", 1, {"bars": [{"close": 101}]})]
    assert stable_content(before) != stable_content(after)


def test_snapshot_includes_committed_wal_without_migrating_source(tmp_path):
    path = tmp_path / "atlas.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE records(kind TEXT,id TEXT,body TEXT)")
        db.execute("CREATE TABLE versions(dataset_id TEXT,version INTEGER,body TEXT)")
        db.execute("INSERT INTO records VALUES('dataset','d',?)", (json.dumps({"id": "d"}),))
        db.commit()
        result = snapshot(path)
        assert result["schema"] == 0
        assert result["records"][("dataset", "d")] == {"id": "d"}
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0


def test_asset_probe_only_collects_same_origin_js_css():
    assets = Assets()
    assets.feed('<script src="/assets/a.js"></script><link href="/assets/b.css">'
                '<script src="https://example.com/other.js"></script><script src="//example.com/a.js"></script>')
    assert assets.urls == {"/assets/a.js", "/assets/b.css"}


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows walkthrough")
def test_existing_work_directory_rejected_before_ports_or_mutation(tmp_path, monkeypatch):
    marker = tmp_path / "keep.txt"
    marker.write_text("preserve")
    walk = Walkthrough(tmp_path, tmp_path / "source", "HEAD", tmp_path / "old.sqlite3")
    monkeypatch.setattr(walk, "ports_free", lambda: pytest.fail("Existing path must be rejected first"))
    with pytest.raises(RuntimeError, match="directorio nuevo"):
        walk.prepare()
    assert marker.read_text() == "preserve"

import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timezone
import json
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from atlas_quant.app import create_app
from atlas_quant.backup import create_backup, restore_backup
from atlas_quant.catalog import RevisionConflict
from atlas_quant.datasets import DatasetService
from atlas_quant.portfolios import PortfolioService
from atlas_quant.quality import EvidenceRequest, RevisionRequest, prepare_evidence, report
from atlas_quant.quality_service import QualityService
from atlas_quant.service import Service
from atlas_quant.store import Store
from tools.atlas_runtime import InstanceLock


def bar(day, price=100):
    return dict(date=day, symbol="TEST", open=float(price), high=float(price), low=float(price),
                close=float(price), volume=10.0, currency="EUR")


def dataset():
    return dict(id="fixture", version=1, bars=[bar("2026-01-02"), bar("2026-01-05", 110)],
                source_kind="observed", source="Fixture declarado", name="D3 fixture")


def evidence(**changes):
    return EvidenceRequest(expected_version=1, symbol="TEST", calendar_name="Calendario sintético",
        market="TEST", timezone="UTC", calendar_source="Fixture independiente D3", calendar_verified=True,
        calendar_csv="date,status,close_at\n2026-01-02,open,2026-01-02T16:00:00+00:00\n2026-01-03,closed,\n2026-01-04,closed,\n2026-01-05,open,2026-01-05T16:00:00+00:00",
        price_basis="raw", basis_verified=True, basis_source="Precios sintéticos sin ajustes",
        availability_csv="date,available_at\n2026-01-02,2026-01-02T16:00:00+00:00\n2026-01-05,2026-01-05T16:00:00+00:00",
        availability_source="Reloj controlado fixture", **changes)


def evidenced():
    value = dataset()
    value["quality_evidence"] = {"TEST": prepare_evidence(evidence(), value)}
    return value


CASES = json.loads((Path(__file__).resolve().parents[2] / "docs/fixtures/v0_4_d3_referencias.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_independent_mark_oracles(case):
    value = dataset()
    value["bars"] = value["bars"][:1]
    if case["calendar"] != "unknown":
        value["quality_evidence"] = {"TEST": {"price_basis":"raw", "basis_verified":True,
            "calendar":{"verified":True, "days":{case["end"]:{"status":case["calendar"],
                "close_at":case["end"]+"T16:00:00+00:00" if case["calendar"] == "open" else None}}}}}
    # Only the 2 January bar exists; the next bar must never supply a past mark.
    result = report(value, "TEST", case["end"], case["end"], today=date(2026, 2, 1))["last"]
    assert (result["status"], result["price"], result["age_days"]) == (
        case["expected_status"], case["expected_price"], case["expected_age"])


def test_capabilities_coverage_basis_availability_and_synthetic():
    value = evidenced()
    good = report(value, "TEST", end="2026-01-05")
    assert good["capabilities"] == dict(draw="allowed", valuation="allowed", exploratory="allowed", historical="allowed", paper="allowed")
    assert [d["status"] for d in good["days"]] == ["observed_session", "market_closed", "market_closed", "observed_session"]
    assert good["days"][1]["price_date"] == "2026-01-02"
    value["source_kind"] = "synthetic"
    assert report(value,"TEST")["capabilities"]["paper"] == "blocked"
    value["source_kind"] = "observed"
    entry = value["quality_evidence"]["TEST"]
    entry["availability"]["2026-01-05"] = "2026-01-06T00:00:00+00:00"
    late = report(value,"TEST")
    assert late["last"]["price"] is None and "not_available_at_cut" in late["last"]["reasons"]
    assert late["capabilities"]["historical"] == "blocked"
    entry["availability"].clear()
    assert report(value,"TEST")["capabilities"]["historical"] == "blocked"
    entry["price_basis"] = "total_return"
    assert report(value,"TEST")["capabilities"]["valuation"] == "blocked"
    assert report(value,"TEST")["capabilities"]["exploratory"] == "blocked"


def test_coverage_end_holes_future_and_pagination():
    value = evidenced()
    out = report(value,"TEST",end="2026-01-06",offset=1,limit=2)
    assert out["last"]["status"] == "calendar_unknown"
    assert out["total_days"] == 5 and len(out["days"]) == 2 and out["offset"] == 1
    value["bars"] = value["bars"][:1]
    missing = report(value,"TEST",end="2026-01-05")
    assert missing["last"]["status"] == "missing_session"
    assert missing["capabilities"]["paper"] == "blocked"
    with pytest.raises(ValueError,match="futuro"):
        report(value,"TEST",end="2026-01-06",today=date(2026,1,5))
    with pytest.raises(ValueError):
        report(value,"TEST",start="2026-02-30")


@pytest.mark.parametrize("change", [
    {"calendar_csv":"date,status,close_at\n2026-01-02,open,2026-01-02T16:00:00"},
    {"calendar_csv":"date,status,close_at\n2026-01-02,closed,\n2026-01-04,closed,"},
    {"calendar_csv":"date,status,close_at\n2026-01-02,closed,\n2026-01-02,closed,"},
    {"calendar_csv":"date,status,close_at\n2026-01-02,closed,2026-01-02T16:00:00Z"},
    {"availability_csv":"date,available_at\n2026-01-03,2026-01-03T16:00:00Z"},
    {"availability_csv":"date,available_at\n2026-01-02,2026-01-01T16:00:00Z"},
    {"timezone":"Inventada/Desconocida"},
])
def test_invalid_evidence_is_rejected(change):
    body = evidence().model_copy(update=change)
    with pytest.raises(ValueError):
        prepare_evidence(body,dataset())


@pytest.fixture
def stored(tmp_path):
    store=Store(tmp_path / "atlas.sqlite3")
    value=dataset()
    saved=DatasetService(store).save_dataset(value["bars"],value["name"],"observed",value["source"])
    return store,saved,QualityService(store)


def test_evidence_atomic_revision_and_backup(stored,tmp_path):
    store,old,quality=stored
    preview=quality.evidence(old["id"],evidence())
    assert store.get_dataset_version(old["id"],2) is None
    committed=quality.evidence(old["id"],evidence().model_copy(update={"commit":True,"preview_token":preview["preview_token"]}))
    assert committed["version"] == 2 and committed["quality"]["capabilities"]["paper"] == "allowed"
    assert store.get_dataset_version(old["id"],1) == old
    assert quality.read(old["id"],1,"TEST")["calendar_verified"] is False
    backup=create_backup(store.path,tmp_path/"backups")
    restore_backup(backup,tmp_path/"restore"/"atlas.sqlite3",tmp_path/"safety",instance_lock=InstanceLock(tmp_path/"restore.lock"))
    restored=Store(tmp_path/"restore"/"atlas.sqlite3")
    assert restored.get_dataset_version(old["id"],2) == store.get_dataset_version(old["id"],2)


def test_confirm_concurrency_and_audit_rollback(stored,monkeypatch):
    store,old,quality=stored
    body=evidence()
    token=quality.evidence(old["id"],body)["preview_token"]
    body=body.model_copy(update={"commit":True,"preview_token":token})
    barrier=Barrier(2)
    def confirm():
        barrier.wait()
        try:
            return quality.evidence(old["id"],body)["committed"]
        except RevisionConflict:
            return False
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:confirm(),range(2)))
    assert sorted(results) == [False,True]
    before=store.get("dataset",old["id"])
    next_body=evidence().model_copy(update={"expected_version":2})
    preview=quality.evidence(old["id"],next_body)
    audit=store.audit_list()
    original=Store._audit
    def fail(db,event,*args):
        if event == "dataset.quality_reviewed":
            raise RuntimeError("rollback")
        return original(db,event,*args)
    monkeypatch.setattr(Store,"_audit",staticmethod(fail))
    with pytest.raises(RuntimeError,match="rollback"):
        quality.evidence(old["id"],next_body.model_copy(update={"commit":True,"preview_token":preview["preview_token"]}))
    assert store.get("dataset",old["id"]) == before
    assert store.get_dataset_version(old["id"],3) is None
    assert store.audit_list() == audit


def csv(bars):
    return "date,symbol,open,high,low,close,volume,currency\n"+"\n".join(
        ",".join(str(b[k]) for k in ("date","symbol","open","high","low","close","volume","currency")) for b in bars)


def test_price_revision_preserves_book_bound_to_original(stored):
    store,old,quality=stored
    store.put("ledger",dict(id=old["id"],events=[dict(id="cash",date="2026-01-02",kind="deposit",amount="1000",currency="EUR")]))
    portfolio=store.atomic(lambda w:w.portfolio_record(w.legacy_portfolio_id(old["id"])))
    before=PortfolioService(store).read(portfolio["id"])
    body=RevisionRequest(expected_version=1,csv=csv([bar("2026-01-02",102),bar("2026-01-03",103),bar("2026-01-05",110)]),reason="Corrección del fixture")
    p=quality.revise(old["id"],body)
    assert (p["changed"],p["added"]) == (1,1)
    quality.revise(old["id"],body.model_copy(update={"commit":True,"preview_token":p["preview_token"]}))
    assert store.get_dataset_version(old["id"],1) == old
    assert PortfolioService(store).read(portfolio["id"]) == before
    assert store.get("dataset",old["id"])["quality_evidence"] == {}
    with pytest.raises(RevisionConflict):
        quality.revise(old["id"],body.model_copy(update={"commit":True,"preview_token":p["preview_token"]}))
    with pytest.raises(ValueError,match="conservar"):
        quality.revise(old["id"],RevisionRequest(expected_version=2,csv=csv([bar("2026-01-02"),bar("2026-01-05")]),reason="Borrar sesión"))


def test_http_quality_protection_validation_and_small_state(tmp_path):
    app=create_app(tmp_path,run_worker=False)
    with TestClient(app) as client:
        response=client.post("/api/datasets",json=dict(csv=csv(dataset()["bars"]),name="D3",source="Fixture D3",source_kind="observed"),headers={"x-atlas-client":"local-v1"})
        assert response.status_code == 200,response.text
        ident=response.json()["id"]
        path=f"/api/datasets/{ident}/quality"
        assert client.post(path,json=evidence().model_dump()).status_code == 403
        p=client.post(path,json=evidence().model_dump(),headers={"x-atlas-client":"local-v1"})
        assert p.status_code == 200,p.text
        commit=evidence().model_dump()|dict(commit=True,preview_token=p.json()["preview_token"])
        assert client.post(path,json=commit,headers={"x-atlas-client":"local-v1"}).status_code == 200
        assert client.get(path,params=dict(version=2,symbol="TEST",limit=1)).json()["total_days"] == 4
        assert client.get(path,params=dict(version=99,symbol="TEST")).status_code == 404
        assert client.get(path,params=dict(version=2,symbol="TEST",limit=501)).status_code == 422
        state=client.get("/api/state")
        assert state.status_code == 200,state.text
        assert "quality_evidence" not in state.text and "calendar_csv" not in state.text


@pytest.mark.parametrize("documented,legacy,base_pass,expected",[(False,False,True,False),(True,False,True,True),(False,True,True,True),(False,False,False,False)])
def test_paper_preserves_other_gates_and_requires_quality(stored,monkeypatch,documented,legacy,base_pass,expected):
    from atlas_quant import service as service_module
    store,value,quality=stored
    if documented:
        p=quality.evidence(value["id"],evidence())
        quality.evidence(value["id"],evidence().model_copy(update={"commit":True,"preview_token":p["preview_token"]}))
    class Frozen(datetime):
        @classmethod
        def now(cls,tz=None):
            return datetime(2026,1,5,17,tzinfo=timezone.utc)
    monkeypatch.setattr(service_module,"datetime",Frozen)
    monkeypatch.setattr(service_module,"evaluate_evidence",lambda *args:dict(passed=base_pass,decision="eligible_paper" if base_pass else "rejected",checks=[],limitations=[]))
    service=Service(store)
    service.update_settings({"kill_switch":False,"max_position_weight":0.25})
    job=service.create_experiment(dict(dataset_id=value["id"],symbol="TEST",provider="none",model=None,
        budget_usd=0,hours=48,auto_paper=True,prompt="Fixture de calidad",costs=dict(initial_cash=1000,
            commission_bps=5,slippage_bps=5,minimum_fee=1,max_position_weight=0.25)))
    assert job["quality_policy"] == "quality-v1"
    job.update(status="observing",phase="forward_observation",observation_started_at="2026-01-05T16:00:00+00:00",
        research={"selected_strategy":{"kind":"buy_hold","symbol":"TEST"}})
    if legacy:
        job.pop("quality_policy")
    store.put("experiment",job)
    asyncio.run(service.observe(job))
    saved=store.get("experiment",job["id"])
    assert saved["gate"]["passed"] is expected
    assert (saved["paper_account"] is not None) is expected
    if not base_pass:
        assert saved["gate"]["decision"] == "rejected"
    if not legacy:
        assert saved["gate"]["checks"][-1]["name"] == "price_quality"


def test_availability_uses_session_timezone_and_preserves_utc_trace():
    value = dataset()
    value["bars"] = value["bars"][:1]
    body = evidence().model_copy(update={
        "timezone": "Pacific/Auckland",
        "calendar_csv": "date,status,close_at\n2026-01-02,open,2026-01-02T01:00:00+13:00",
        "availability_csv": "date,available_at\n2026-01-02,2026-01-01T12:00:00Z",
    })
    value["quality_evidence"] = {"TEST": prepare_evidence(body, value)}
    result = report(value, "TEST")
    assert result["calendar_timezone"] == "Pacific/Auckland"
    assert result["last"]["available_at"] == result["last"]["close_at"] == "2026-01-01T12:00:00+00:00"
    assert result["capabilities"]["historical"] == "allowed"


def test_revised_prices_do_not_recalculate_frozen_observation(stored):
    store,value,quality=stored
    service=Service(store)
    job=service.create_experiment(dict(dataset_id=value["id"],symbol="TEST",provider="none",model=None,
        budget_usd=0,hours=48,auto_paper=False,prompt="Conservar histórico",costs=dict(initial_cash=1000)))
    job.update(status="observing",research={"original":"unchanged"},observation={"original":True})
    store.put("experiment",job)
    body=RevisionRequest(expected_version=1,csv=csv([bar("2026-01-02",102),bar("2026-01-05",110)]),reason="Revisión controlada")
    p=quality.revise(value["id"],body)
    quality.revise(value["id"],body.model_copy(update={"commit":True,"preview_token":p["preview_token"]}))
    asyncio.run(service.tick())
    saved=store.get("experiment",job["id"])
    assert saved["status"] == "failed" and "revisado" in saved["error"]
    assert saved["research"] == job["research"] and saved["observation"] == job["observation"]

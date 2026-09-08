"""Local, in-memory projection benchmark; no application, network or user store.

Usage: python tools/benchmarks/benchmark_v03_prices.py
"""
import gc
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from time import perf_counter
import tracemalloc

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "validation"
OUTPUT.mkdir(parents=True, exist_ok=True)
build_manifest = ROOT / "frontend" / "dist" / "atlas-build.json"
frontend_build_sources = (json.loads(build_manifest.read_text(encoding="utf-8"))["sources"]
                          if build_manifest.is_file() else None)
sys.path.insert(0, str(ROOT / "backend"))
from atlas_quant.contracts import DatasetPricesResponse
from atlas_quant.data import build_provenance_manifest
from atlas_quant.prices import project_prices


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def measure(function, count=7):
    samples = []
    for _ in range(count):
        gc.collect()
        begin = perf_counter()
        result = function()
        samples.append((perf_counter() - begin) * 1000)
        del result
    return {"samples_ms": samples, "median_ms": statistics.median(samples),
            "min_ms": min(samples), "max_ms": max(samples)}


results = []
for size in (1000, 10000, 100000):
    bars = [{"date": (date(1700, 1, 1) + timedelta(days=index)).isoformat(), "symbol": "BENCH",
             "open": 100.125, "high": 102.5, "low": 99.75, "close": 101.0625,
             "volume": float(index % 10000), "currency": "EUR"} for index in range(size)]
    snapshot = {"id": f"synthetic-benchmark-{size}", "version": 1, "bars": bars,
                "source_kind": "synthetic", "source": "Offline benchmark only"}
    snapshot["manifest"] = build_provenance_manifest(bars, "Projection benchmark", "synthetic", snapshot["source"])
    before = digest(snapshot)
    projected = project_prices(snapshot, "BENCH")
    assert len(projected["bars"]) == size
    assert projected["first_date"] == bars[0]["date"] and projected["last_date"] == bars[-1]["date"]
    assert projected["preceding_close"] is None
    timing = measure(lambda: project_prices(snapshot, "BENCH"))
    validation = measure(lambda: DatasetPricesResponse.model_validate(projected))
    narrow = measure(lambda: project_prices(snapshot, "BENCH", start=bars[-100]["date"]))
    tracemalloc.start()
    projection_with_trace = project_prices(snapshot, "BENCH")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(projection_with_trace["bars"]) == size
    assert digest(snapshot) == before
    results.append({"daily_observations": size, "projection": timing, "pydantic_validation": validation,
                    "projection_last_100": narrow, "projection_peak_tracemalloc_bytes": peak,
                    "json_response_bytes": len(DatasetPricesResponse.model_validate(projected).model_dump_json().encode()),
                    "snapshot_sha256_unchanged": before})

report = {"at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
          "frontend_build_sources_sha256": frontend_build_sources,
          "platform": platform.platform(), "scope": "In-memory daily-price projection and DTO validation; no HTTP, SQLite, browser or network.",
          "synthetic_only": True, "ordinary_database_opened": False, "app_started": False,
          "iterations_per_timing": 7, "source": "backend/atlas_quant/prices.py project_prices",
          "limits": "One machine, sequential execution, no latency SLA implied; timings exclude source deserialization and transmission.",
          "results": results}
target = OUTPUT / "v03-prices-projection-benchmark.json"
target.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"report": str(target), "results": [{"n": item["daily_observations"],
      "projection_median_ms": item["projection"]["median_ms"],
      "validation_median_ms": item["pydantic_validation"]["median_ms"],
      "last_100_median_ms": item["projection_last_100"]["median_ms"],
      "peak_mib": item["projection_peak_tracemalloc_bytes"] / 1024 / 1024,
      "response_bytes": item["json_response_bytes"]} for item in results]}, indent=2))

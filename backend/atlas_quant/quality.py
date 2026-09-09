"""Pure, version-bound daily price quality. Never infer calendars or fill bars."""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field

from .data import _rows, _iso_date

MAX_DAYS = 36_600
POLICY = "quality-v1"
EXPLORATORY_WARNING = "Investigación exploratoria: la cobertura o disponibilidad histórica no están acreditadas; no autoriza promoción paper."


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":")).encode()).hexdigest()


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or "T" not in value:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError, AttributeError) as exc:
        raise ValueError("Timestamp requerido con fecha, T, hora y offset UTC explícito.") from exc


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    symbol: str = Field(min_length=1, max_length=40)
    calendar_name: str = Field(default="", max_length=100)
    market: str = Field(default="", max_length=50)
    timezone: str = Field(default="UTC", max_length=100)
    calendar_source: str = Field(default="", max_length=500)
    calendar_verified: bool = False
    calendar_csv: str = Field(default="", max_length=4_000_000)
    price_basis: Literal["raw", "split_adjusted", "total_return", "unknown"] = "unknown"
    basis_verified: bool = False
    basis_source: str = Field(default="", max_length=500)
    availability_csv: str = Field(default="", max_length=4_000_000)
    availability_source: str = Field(default="", max_length=500)


class EvidenceRequest(EvidenceInput):
    expected_version: int = Field(ge=1)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_version: int = Field(ge=1)
    csv: str = Field(min_length=1, max_length=8_000_000)
    reason: str = Field(min_length=3, max_length=500)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def prepare_evidence(body: EvidenceInput, dataset):
    symbol = body.symbol.upper()
    dates = {bar["date"] for bar in dataset["bars"] if bar["symbol"] == symbol}
    if not dates:
        raise ValueError("Símbolo ausente en esta versión.")
    try:
        zone = ZoneInfo(body.timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Zona IANA no disponible en esta instalación.") from exc
    calendar = None
    if body.calendar_csv:
        if not body.calendar_name or not body.market or len(body.calendar_source) < 3:
            raise ValueError("Calendario: indica nombre, mercado y procedencia.")
        days = {}
        for line, row in _rows(body.calendar_csv, {"date", "status", "close_at"}, {"date", "status", "close_at"}):
            day = _iso_date(row["date"], line)
            if day in days or row["status"] not in ("open", "closed"):
                raise ValueError("Calendario con fecha duplicada o estado distinto de open/closed.")
            close = None
            if row["status"] == "open":
                close_dt = timestamp(row["close_at"])
                if close_dt.astimezone(zone).date().isoformat() != day:
                    raise ValueError("La hora de cierre debe pertenecer al día de sesión en su zona.")
                close = close_dt.isoformat()
            elif row["close_at"]:
                raise ValueError("Un día cerrado no lleva hora de cierre.")
            days[day] = dict(status=row["status"], close_at=close)
            if len(days) > MAX_DAYS:
                raise ValueError("Calendario demasiado largo.")
        if not days:
            raise ValueError("Calendario vacío.")
        first, last = min(days), max(days)
        if (date.fromisoformat(last) - date.fromisoformat(first)).days + 1 != len(days):
            raise ValueError("El calendario debe declarar todos los días dentro de su cobertura.")
        calendar = dict(name=body.calendar_name, market=body.market, timezone=body.timezone,
            source=body.calendar_source, verified=body.calendar_verified, start=first, end=last, days=days)
    elif body.calendar_verified:
        raise ValueError("No se puede verificar un calendario sin días explícitos.")
    if body.basis_verified and (body.price_basis == "unknown" or len(body.basis_source) < 3):
        raise ValueError("Verificar la base requiere una base conocida y procedencia.")
    availability = {}
    if body.availability_csv:
        if len(body.availability_source) < 3:
            raise ValueError("Indica la procedencia de la disponibilidad histórica.")
        for line, row in _rows(body.availability_csv, {"date", "available_at"}, {"date", "available_at"}):
            day = _iso_date(row["date"], line)
            if day not in dates or day in availability:
                raise ValueError("Disponibilidad duplicada o sin barra de precios correspondiente.")
            value = timestamp(row["available_at"]).isoformat() if row["available_at"] else None
            if value and timestamp(value).astimezone(zone).date().isoformat() < day:
                raise ValueError("Una barra diaria completa no puede estar disponible antes de su fecha.")
            availability[day] = value
    return dict(symbol=symbol, calendar=calendar, price_basis=body.price_basis,
        basis_verified=body.basis_verified, basis_source=body.basis_source,
        availability=availability, availability_source=body.availability_source)


def report(dataset, symbol, start=None, end=None, *, offset=0, limit=100, today=None):
    bars = sorted((b for b in dataset["bars"] if b["symbol"] == symbol), key=lambda b: b["date"])
    if not bars:
        raise ValueError("Símbolo ausente en esta versión.")
    today = today or datetime.now(timezone.utc).date()
    end = _iso_date(end or bars[-1]["date"], 0)
    start = _iso_date(start or bars[0]["date"], 0)
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    total = (last - first).days + 1
    if total < 1 or total > MAX_DAYS or last > today:
        raise ValueError("El período debe estar ordenado, no ser futuro y tener como máximo 36.600 días.")
    evidence = dataset.get("quality_evidence", {}).get(symbol, {})
    calendar = evidence.get("calendar") or {}
    days = calendar.get("days", {}) if calendar.get("verified") else {}
    opens = sorted(day for day, row in days.items() if row["status"] == "open")
    dates = [b["date"] for b in bars]
    indexed = {b["date"]: b for b in bars}
    availability = evidence.get("availability", {})
    basis_ok = evidence.get("price_basis") == "raw" and evidence.get("basis_verified") is True
    corporate = any(a["symbol"] == symbol and a["date"] <= end for a in dataset.get("corporate_actions", []))
    counts, result_rows = Counter(), []
    known_coverage = True
    historical_ok = True
    range_invalid = False
    last_row = None
    for index in range(total):
        day = (first + timedelta(days=index)).isoformat()
        entry = days.get(day)
        pos = bisect_right(dates, day) - 1
        mark = bars[pos] if pos >= 0 else None
        age = (date.fromisoformat(day) - date.fromisoformat(mark["date"])).days if mark else None
        prior = bisect_right(opens, day) - 1
        expected = opens[prior] if prior >= 0 else None
        coherent = bool(entry and mark and expected == mark["date"])
        status = "observed_session"
        reasons = []
        if not entry:
            status = "calendar_unknown"
            known_coverage = False
        elif entry["status"] == "closed":
            status = "unexpected_bar" if day in indexed else "market_closed"
        elif day not in indexed:
            status = "missing_session"
        if not mark:
            status = "missing_price"
        elif age > 7 and not coherent:
            status = "stale_mark"
        # A close observed on a declared closed date cannot be carried as valid later.
        invalid_mark = bool(mark and days.get(mark["date"], {}).get("status") == "closed")
        if invalid_mark:
            reasons.append("unexpected_bar")
        if status in ("calendar_unknown", "missing_session", "missing_price", "stale_mark", "unexpected_bar"):
            reasons.append(status)
        if not basis_ok:
            reasons.append("price_basis_unverified" if evidence.get("price_basis", "unknown") in ("raw", "unknown") else "price_basis_incompatible")
        if corporate:
            reasons.append("corporate_action_unresolved")
        if mark:
            known_at = availability.get(mark["date"])
            mark_session = days.get(mark["date"], {})
            decision = mark_session.get("close_at")
            if not known_at:
                historical_ok = False
                reasons.append("availability_unknown")
            elif not decision or timestamp(known_at) > timestamp(decision):
                historical_ok = False
                reasons.append("not_available_at_close")
            cutoff = entry.get("close_at") if entry else None
            cutoff = cutoff or day + "T23:59:59.999999+00:00"
            if known_at and timestamp(known_at) > timestamp(cutoff):
                reasons.append("not_available_at_cut")
        blocked = status in ("missing_price", "stale_mark", "unexpected_bar") or invalid_mark or "not_available_at_cut" in reasons or corporate or (evidence.get("price_basis") in ("split_adjusted", "total_return"))
        if entry and status in ("missing_session", "missing_price", "unexpected_bar") or invalid_mark or "not_available_at_cut" in reasons:
            range_invalid = True
        quality = "blocked" if blocked else "allowed" if coherent and basis_ok else "provisional"
        row = dict(date=day, status=status, price_date=mark["date"] if mark else None,
            age_days=age, price=float(mark["close"]) if mark and not blocked else None,
            close_at=entry.get("close_at") if entry else None,
            available_at=availability.get(mark["date"]) if mark else None,
            valuation=quality, reasons=list(dict.fromkeys(reasons)))
        counts[status] += 1
        last_row = row
        if offset <= index < offset + limit:
            result_rows.append(row)
    exploratory = "blocked" if range_invalid or corporate or evidence.get("price_basis") in ("split_adjusted", "total_return") else "allowed" if known_coverage and basis_ok else "provisional"
    historical = "allowed" if exploratory == "allowed" and historical_ok else "blocked"
    paper = historical == "allowed" and last_row["valuation"] == "allowed" and dataset["source_kind"] == "observed" and not dataset.get("feed", {}).get("error")
    return dict(policy=POLICY, dataset_id=dataset["id"], dataset_version=dataset["version"], symbol=symbol,
        start=start, end=end, evidence_hash=digest(evidence), calendar_name=calendar.get("name"),
        calendar_verified=bool(calendar.get("verified")), calendar_source=calendar.get("source"),
        calendar_market=calendar.get("market"), calendar_timezone=calendar.get("timezone"),
        price_basis=evidence.get("price_basis", "unknown"), basis_verified=bool(evidence.get("basis_verified")),
        capabilities=dict(draw="allowed", valuation=last_row["valuation"], exploratory=exploratory,
                          historical=historical, paper="allowed" if paper else "blocked"),
        counts=dict(counts), total_days=total, offset=offset, days=result_rows, last=last_row,
        warnings=["La calidad de precios no acredita por sí sola contabilidad, identidad, FX o conciliación.",
                  "Disponibilidad desconocida no equivale a datos conocidos entonces."])


def check_research(dataset, symbol):
    quality = report(dataset, symbol, limit=0)
    if quality["capabilities"]["exploratory"] == "blocked":
        raise ValueError("Calidad de precios incompatible con nueva investigación: revisa cobertura, base y eventos pendientes en Datos.")
    return quality

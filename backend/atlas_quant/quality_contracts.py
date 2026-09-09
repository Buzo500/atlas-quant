"""Bounded public quality reports; evidence bodies stay out of routine state."""
from typing import Literal
from .contracts import ResponseModel

Capability = Literal["allowed", "provisional", "blocked"]


class QualityDay(ResponseModel):
    close_at: str | None = None
    available_at: str | None = None
    date: str
    status: Literal["observed_session", "market_closed", "calendar_unknown", "missing_session", "missing_price", "stale_mark", "unexpected_bar"]
    price_date: str | None
    age_days: int | None
    price: float | None
    valuation: Capability
    reasons: list[str]


class QualityCapabilities(ResponseModel):
    draw: Capability
    valuation: Capability
    exploratory: Capability
    historical: Capability
    paper: Capability


class QualityReport(ResponseModel):
    calendar_market: str | None = None
    calendar_timezone: str | None = None
    policy: Literal["quality-v1"]
    dataset_id: str
    dataset_version: int
    symbol: str
    start: str
    end: str
    evidence_hash: str
    calendar_name: str | None
    calendar_verified: bool
    calendar_source: str | None
    price_basis: Literal["raw", "split_adjusted", "total_return", "unknown"]
    basis_verified: bool
    capabilities: QualityCapabilities
    counts: dict[str, int]
    total_days: int
    offset: int
    days: list[QualityDay]
    last: QualityDay
    warnings: list[str]


class EvidencePreview(ResponseModel):
    dataset_id: str
    version: int
    committed: bool
    preview_token: str
    quality: QualityReport


class RevisionPreview(ResponseModel):
    dataset_id: str
    version: int
    committed: bool
    preview_token: str
    changed: int
    added: int
    affected_symbols: list[str]
    feed_paused: bool

"""Versioned, bounded inputs and explicit availability for asset comparisons."""
from datetime import date, datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .contracts import ResponseModel


class AssetSourceRef(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    kind: Literal['native', 'legacy']
    id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    symbol: str = Field(min_length=1, max_length=64)


class AnalysisFxRef(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)


class AssetAnalysisInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    sources: list[AssetSourceRef] = Field(min_length=1, max_length=12)
    start_date: str
    end_date: str
    fx: AnalysisFxRef | None = None
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode='after')
    def validate_period(self):
        start, end = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
        if start.isoformat() != self.start_date or end.isoformat() != self.end_date:
            raise ValueError('Fechas ISO YYYY-MM-DD requeridas.')
        if not 1 <= (end-start).days <= 3660 or end >= datetime.now(timezone.utc).date():
            raise ValueError('El periodo debe tener entre 1 y 3.660 días y terminar antes del día UTC en curso.')
        keys = [(s.kind, s.id, s.symbol) for s in self.sources]
        if len(keys) != len(set(keys)):
            raise ValueError('Elige cada fuente/activo una sola vez.')
        return self


class AssetSource(ResponseModel):
    key: str
    ref: AssetSourceRef
    name: str
    dataset_name: str
    source: str
    instrument_id: str
    instrument_type: str
    listing_id: str
    market: str | None
    currency: Literal['EUR', 'USD']
    sha256: str
    date_min: str
    date_max: str
    row_count: int


class AnalysisFxSource(ResponseModel):
    ref: AnalysisFxRef
    name: str
    source: str
    sha256: str
    date_min: str
    date_max: str


class AssetSourceCatalog(ResponseModel):
    sources: list[AssetSource]
    fx: list[AnalysisFxSource]
    limit: int


class AssetProfile(ResponseModel):
    source: AssetSource
    status: Literal['complete', 'partial', 'unavailable']
    reasons: list[str]
    expected_sessions: int
    observed_sessions: int
    valid_sessions: int
    valid_intervals: int
    first_date: str | None
    last_date: str | None
    last_close_native: str | None
    last_close_eur: str | None
    price_change_pct: str | None
    session_volatility_pct: str | None
    annualized_volatility_pct: str | None
    max_drawdown_pct: str | None
    historical_known: bool
    known_dividends: int


class AssetComparisonRow(ResponseModel):
    source_key: str
    start_eur: str
    end_eur: str
    price_change_pct: str


class AssetComparisonPoint(ResponseModel):
    date: str
    indices: list[str]


class AssetComparison(ResponseModel):
    start_date: str | None
    end_date: str | None
    rows: list[AssetComparisonRow]
    points: list[AssetComparisonPoint]
    reasons: list[str]


class CorrelationCell(ResponseModel):
    left: str
    right: str
    value: str | None
    reason: str | None


class CorrelationInterval(ResponseModel):
    start_date: str
    end_date: str


class AssetCorrelations(ResponseModel):
    method: Literal['pearson-simple-returns']
    minimum_observations: int
    observations: int
    intervals: list[CorrelationInterval]
    cells: list[CorrelationCell]
    reasons: list[str]


class AssetAnalysisResult(ResponseModel):
    profiles: list[AssetProfile]
    comparison: AssetComparison
    correlations: AssetCorrelations
    fx: AnalysisFxSource | None
    currency: Literal['EUR']
    basis: Literal['raw-price-excluding-dividends']
    annualization_sessions: int
    warnings: list[str]


class AssetAnalysisReport(ResponseModel):
    id: str
    created_at: str
    policy: Literal['atlas-asset-analysis-v1']
    context_hash: str
    catalog_revision: int
    corporate_revision: int
    inputs: AssetAnalysisInput
    result: AssetAnalysisResult
    current: bool
    saved: bool


class AssetAnalysisPreview(ResponseModel):
    report: AssetAnalysisReport
    preview_token: str
    committed: bool


class AssetAnalysisSummary(ResponseModel):
    id: str
    created_at: str
    start_date: str
    end_date: str
    names: list[str]


class AssetAnalysisHistory(ResponseModel):
    reports: list[AssetAnalysisSummary]
    offset: int
    limit: int

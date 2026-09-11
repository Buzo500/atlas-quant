"""Versioned laboratory inputs and deliberately bounded public results."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .contracts import ResponseModel
from .book import cutoff
from .simulation_contracts import SimulationConfig
from .walk_forward_contracts import WalkForwardConfig, WalkForwardSummary

POLICY = 'atlas-lab-temporal-v1'


class LabInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    name: str = Field(min_length=3, max_length=100)
    series_id: str = Field(min_length=1, max_length=100)
    series_version: int = Field(ge=1)
    start_date: str
    holdout_date: str
    end_date: str
    fast: int = Field(default=20, ge=2, le=249)
    slow: int = Field(default=50, ge=3, le=250)
    sessions_csv: str = Field(min_length=1, max_length=500_000)
    opening_source: str = Field(min_length=3, max_length=500)
    event_free_source: str = Field(min_length=3, max_length=500)
    evidence_reviewed: bool
    config: SimulationConfig
    walk_forward: WalkForwardConfig | None = None

    @field_validator('start_date', 'holdout_date', 'end_date')
    @classmethod
    def date(cls, value):
        return cutoff(value)


class LabOpenInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    protocol_hash: str = Field(pattern=r'^[0-9a-f]{64}$')
    acknowledge_exposure: Literal[True]

    @field_validator('acknowledge_exposure', mode='before')
    @classmethod
    def exact_true(cls, value):
        if value is not True:
            raise ValueError('Confirma que abrir la prueba final consume su reserva.')
        return value


class LabPoint(ResponseModel):
    date: str
    sma_eur: str | None
    buy_hold_eur: str | None
    cash_eur: str


class LabMetric(ResponseModel):
    name: Literal['SMA', 'Comprar y mantener', 'Efectivo']
    final_nav_eur: str | None
    return_pct: str | None
    max_drawdown_pct: str | None
    fills: int
    fees_eur: str


class LabTrade(ResponseModel):
    strategy: Literal['SMA', 'Comprar y mantener']
    date: str
    side: Literal['buy', 'sell']
    quantity: str
    price_eur: str
    fee_eur: str


class LabPeriod(ResponseModel):
    start_date: str
    end_date: str
    sessions: int
    metrics: list[LabMetric]
    curve: list[LabPoint]
    trades: list[LabTrade]
    rejected: int
    expired: int
    report_hash: str


class WalkForwardWindow(ResponseModel):
    index: int
    context_start: str
    context_end: str
    warmup_start: str
    warmup_sessions: int
    context_metrics: list[LabMetric]
    context_hash: str
    evaluation: LabPeriod
    evaluable: bool
    passed: bool
    reasons: list[str]


class WalkForwardReport(ResponseModel):
    policy: Literal['atlas-walk-forward-fixed-v1']
    config: WalkForwardConfig
    windows: list[WalkForwardWindow]
    summary: WalkForwardSummary
    unused_sessions: int
    unused_start: str | None
    unused_end: str | None
    warnings: list[str]
    report_hash: str


class LabSummary(ResponseModel):
    id: str
    name: str
    created_at: str
    policy: Literal['atlas-lab-temporal-v1']
    instrument_id: str
    listing_id: str
    series_id: str
    series_version: int
    source_hash: str
    start_date: str
    holdout_date: str
    end_date: str
    opened: bool
    fast: int
    slow: int


class LabHistory(ResponseModel):
    items: list[LabSummary]
    offset: int
    limit: int


class LabReport(ResponseModel):
    protocol: LabSummary
    config: SimulationConfig
    development: LabPeriod
    holdout: LabPeriod | None
    warnings: list[str]
    evidence_hash: str
    walk_forward: WalkForwardReport | None = None


class LabReproduction(ResponseModel):
    id: str
    development_matches: bool
    holdout_matches: bool | None
    walk_forward_matches: bool | None = None

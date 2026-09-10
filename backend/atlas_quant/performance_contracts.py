"""Exact accounting amounts and explicitly qualified fractional return rates."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .contracts import ResponseModel
from .identity_contracts import PriceBinding
from .market_contracts import FxBinding
from .valuation_contracts import ExternalFlow, Mark, Status


class PerformanceMetric(ResponseModel):
    value: str | None
    status: Literal['complete', 'provisional', 'incomplete', 'unavailable']
    reasons: list[str]


class PnlMetric(PerformanceMetric):
    display_value: str | None


class ReturnSegment(PerformanceMetric):
    start_date: str
    end_date: str


class TimeWeighted(PerformanceMetric):
    convention: Literal['daily-external-flows-at-close']
    start_date: str | None
    end_date: str
    segments: list[ReturnSegment]


class MoneyWeighted(PerformanceMetric):
    convention: Literal['actual-days/365']
    domain: list[str]
    iterations: int
    bracket_width: str | None
    normalized_residual: str | None
    rate_tolerance: str
    residual_tolerance: str
    max_iterations: int


class PerformancePoint(ResponseModel):
    date: str
    nav: str | None
    nav_exact: str | None
    flow_eur: str | None
    status: Status
    twr_factor: str | None
    historical_known: bool
    reasons: list[str]


class CostItem(ResponseModel):
    event_id: str
    date: str
    kind: Literal['fee', 'tax', 'charge']
    currency: Literal['EUR', 'USD']
    native_amount: str
    eur_amount: str | None
    status: Status
    fx: Mark | None


class PriceHead(ResponseModel):
    series_id: str
    version: int | None


class PerformanceSources(ResponseModel):
    portfolio_id: str
    portfolio_revision: int
    catalog_revision: int
    corporate_revision: int
    bindings: list[PriceBinding]
    fx_binding: FxBinding | None
    price_heads: list[PriceHead]
    fx_head: int | None


class PerformanceReport(ResponseModel):
    id: str
    portfolio_id: str
    portfolio_revision: int
    context_hash: str
    created_at: str
    current: bool
    saved: bool
    policy: Literal['atlas-performance-v1']
    start_date: str
    end_date: str
    initial_nav: str | None
    final_nav: str | None
    external_net: PerformanceMetric
    pnl: PnlMetric
    twr: TimeWeighted
    mwr: MoneyWeighted
    costs: list[CostItem]
    costs_eur: PerformanceMetric
    flows: list[ExternalFlow]
    points: list[PerformancePoint]
    unlinked_payments: list[str]
    historical_known: bool
    source_context: PerformanceSources


class PerformanceInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    start_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    end_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    expected_revision: int = Field(ge=1)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class PerformancePreview(ResponseModel):
    report: PerformanceReport
    committed: bool
    preview_token: str


class PerformanceSummary(ResponseModel):
    id: str
    portfolio_id: str
    portfolio_revision: int
    start_date: str
    end_date: str
    created_at: str
    pnl: PnlMetric
    twr: PerformanceMetric
    mwr: PerformanceMetric


class PerformanceHistory(ResponseModel):
    reports: list[PerformanceSummary]
    offset: int
    limit: int

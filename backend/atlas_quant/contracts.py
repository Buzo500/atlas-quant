"""Public response contracts for the local API.

The HTTP boundary validates persisted/domain results instead of silently exposing
untyped dictionaries. Optional fields describe lifecycle stages and old records;
routes use ``response_model_exclude_unset=True`` to preserve their wire shape.
Arbitrary JSON is restricted to the audit payload and heterogeneous gate evidence.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


Provider = Literal["none", "openai", "anthropic"]
ExperimentStatus = Literal[
    "queued", "running", "observing", "eligible_paper", "paused", "cancelled",
    "completed", "failed", "interrupted",
]


class ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class HealthResponse(ResponseModel):
    status: Literal["ok", "worker_failed"]
    version: str
    mode: Literal["local"]
    live_available: Literal[False]
    worker_interval_seconds: int


class SettingsResponse(ResponseModel):
    id: str
    kill_switch: bool
    max_position_weight: float = Field(gt=0, le=1)
    mode: Literal["paper"]
    live_available: Literal[False]


class ProviderModel(ResponseModel):
    id: str
    input_per_million: float
    output_per_million: float


class ProviderResponse(ResponseModel):
    provider: Literal["openai", "anthropic"]
    configured: bool
    models: list[ProviderModel]


class AuditEntry(ResponseModel):
    seq: int
    at: str
    event: str
    entity: str | None
    details: dict[str, JsonValue]


class Manifest(ResponseModel):
    schema_version: str
    hash_algorithm: Literal["sha256"]
    hash_version: int
    sha256: str
    name: str
    source_kind: Literal["observed", "synthetic"]
    source: str
    generated_at: str
    date_min: str
    date_max: str
    symbols: list[str]
    row_count: int
    counts_by_symbol: dict[str, int]
    currencies: list[str]
    synthetic: bool
    price_basis: str
    calendar: str
    warnings: list[str]


class FeedResponse(ResponseModel):
    symbol: str
    start: str
    last_attempt: str
    error: str | None
    interval_hours: float
    request_id: str | None = Field(default=None, exclude=True)


class CorporateAction(ResponseModel):
    date: str
    symbol: str
    kind: Literal["dividend", "split", "capital_gain"]
    value: float
    currency: Literal["EUR"]
    applied_to_ledger: Literal[False]


class SourceMetadata(ResponseModel):
    provider: str
    adapter: str
    adapter_version: str
    symbol: str
    currency: Literal["EUR"]
    currency_verified: bool
    instrument_type: Literal["EQUITY", "ETF"]
    exchange: str | None
    exchange_timezone: str | None
    interval: str
    is_realtime: bool
    auto_adjust: bool
    back_adjust: bool
    repair: bool
    price_basis: str
    start_inclusive: str
    end_exclusive: str
    fetched_at: str
    closed_before_utc_date: str
    corporate_actions_present: bool
    corporate_actions_applied: bool
    action_columns: list[str]
    received_rows: int
    accepted_rows: int
    excluded_out_of_range_rows: int
    excluded_empty_quote_rows: int
    excluded_empty_quote_dates: list[str]
    documentation: str
    request_timeout_seconds: float
    fetch_deadline_seconds: float


class DatasetResponse(ResponseModel):
    id: str
    name: str
    source_kind: Literal["observed", "synthetic"]
    source: str
    manifest: Manifest
    version: int
    updated_at: str
    demo: bool | None = None
    feed: FeedResponse | None = None
    restored_feed: FeedResponse | None = None
    corporate_actions: list[CorporateAction] | None = None
    source_metadata: SourceMetadata | None = None
    warnings: list[str] | None = None


class DatasetPriceBar(ResponseModel):
    date: str
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class DatasetPricesResponse(ResponseModel):
    dataset_id: str
    dataset_version: int = Field(ge=1)
    manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    symbol: str
    currency: Literal["EUR"]
    source_kind: Literal["observed", "synthetic"]
    source: str
    source_metadata: SourceMetadata | None
    price_basis: str
    calendar: str
    warnings: list[str]
    available_start: str = Field(description="Primera sesión disponible del símbolo en esta versión.")
    available_end: str = Field(description="Última sesión disponible del símbolo en esta versión.")
    first_date: str | None = Field(description="Primera sesión del intervalo solicitado, o null si está vacío.")
    last_date: str | None = Field(description="Última sesión del intervalo solicitado, o null si está vacío.")
    preceding_close: float | None = Field(description="Cierre de la sesión anterior a la primera barra devuelta, si existe.")
    preceding_date: str | None
    bars: list[DatasetPriceBar] = Field(max_length=100_000)


class Position(ResponseModel):
    symbol: str
    quantity: float
    price: float
    price_date: str
    market_value: float
    weight: float
    cost_basis: float
    unrealized_pnl: float


class PortfolioPoint(ResponseModel):
    date: str
    nav: float
    twr_index: float


class PortfolioResponse(ResponseModel):
    nav: float
    cash: float
    net_contributions: float
    pnl: float
    twr: float
    positions: list[Position]
    curve: list[PortfolioPoint]
    warnings: list[str]


class LedgerResponse(ResponseModel):
    added: int
    duplicates: int
    total: int
    committed: bool
    portfolio: PortfolioResponse
    preview_token: str = Field(pattern=r"^[0-9a-f]{64}$")


class Strategy(ResponseModel):
    kind: Literal["buy_hold", "sma_cross", "momentum"]
    symbol: str
    fast_window: int | None = None
    slow_window: int | None = None
    lookback: int | None = None
    top_k: int | None = None
    rationale: str | None = None


class CostsResponse(ResponseModel):
    initial_cash: float
    commission_bps: float
    slippage_bps: float
    minimum_fee: float
    max_position_weight: float


class PolicyResponse(ResponseModel):
    min_oos_observations: int
    min_trades: int
    min_sharpe: float
    max_drawdown: float
    min_excess_return: float
    min_forward_sessions: int
    requested_hours: float


class Metrics(ResponseModel):
    total_return: float
    annualized_return: float | None
    volatility: float
    sharpe: float | None
    max_drawdown: float
    trade_count: int
    costs: float
    benchmark_return: float
    excess_return: float
    observations: int


class BacktestPoint(ResponseModel):
    date: str
    equity: float
    benchmark: float


class Trade(ResponseModel):
    date: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    price: float
    fee: float


class BacktestResponse(ResponseModel):
    metrics: Metrics
    curve: list[BacktestPoint]
    trades: list[Trade]
    warnings: list[str]
    final_cash: float
    final_quantity: int
    strategy: Strategy
    max_position_weight: float


class Period(ResponseModel):
    start: str
    end: str
    observations: int


class CandidateResult(ResponseModel):
    strategy: Strategy
    validation_metrics: Metrics


class SensitivityResult(ResponseModel):
    cost_multiplier: float
    period: Literal["test"]
    metrics: Metrics


class ResearchExecution(ResponseModel):
    """Immutable identity of the snapshot and inputs used by a manual run."""
    id: str
    dataset_id: str
    dataset_name: str
    dataset_version: int
    dataset_manifest_hash: str
    symbol: str
    costs: CostsResponse
    started_at: str
    completed_at: str
    period: Period


class ResearchResult(ResponseModel):
    """A persisted research checkpoint can contain only its frozen strategy."""
    selected_strategy: Strategy
    candidate_results: list[CandidateResult] | None = None
    train_period: Period | None = None
    validation_period: Period | None = None
    test_period: Period | None = None
    out_of_sample: BacktestResponse | None = None
    full_result: BacktestResponse | None = None
    sensitivity: list[SensitivityResult] | None = None
    data_hash: str | None = None
    warnings: list[str] | None = None
    max_position_weight: float | None = None
    execution: ResearchExecution | None = None


class ResearchResponse(ResearchResult):
    """A completed manual research response requires the complete evidence."""
    candidate_results: list[CandidateResult]
    train_period: Period
    validation_period: Period
    test_period: Period
    out_of_sample: BacktestResponse
    full_result: BacktestResponse
    sensitivity: list[SensitivityResult]
    data_hash: str
    warnings: list[str]
    max_position_weight: float
    execution: ResearchExecution


class Plan(ResponseModel):
    hypothesis: str
    candidates: list[Strategy]
    risks: list[str]
    horizon_hours: float | None = None


class Usage(ResponseModel):
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class Summary(ResponseModel):
    summary: str
    limitations: list[str]
    recommendation: Literal["reject", "continue_observation", "consider_paper"]
    provider: Provider
    model: str | None = None
    usage: Usage | None = None


class Observation(ResponseModel):
    elapsed_hours: float | None = None
    new_sessions: int | None = None
    source_kind: Literal["observed", "synthetic"] | None = None
    reconciled: bool | None = None
    forward_metrics: Metrics | None = None
    last_date: str | None = None


class GateCheck(ResponseModel):
    name: str
    passed: bool
    actual: JsonValue
    required: JsonValue
    reason: str


class Gate(ResponseModel):
    passed: bool
    decision: Literal["eligible_paper", "observe", "rejected"]
    checks: list[GateCheck]
    limitations: list[str]


class PaperOrder(ResponseModel):
    id: str
    symbol: str
    side: Literal["buy", "sell"]
    status: Literal["pending", "filled", "rejected", "cancelled"]
    signal_date: str
    signal_price: float
    quantity: int | None
    target_weight: float
    execution: Literal["next_observed_open"]
    simulated: Literal[True]
    reason: str | None = None
    cancelled_at_date: str | None = None
    rejected_at_date: str | None = None
    filled_at_date: str | None = None
    price: float | None = None
    fee: float | None = None


class PaperFill(Trade):
    id: str
    order_id: str
    signal_date: str
    cash_after: float
    position_after: int
    position_weight_at_fill: float
    simulated: Literal[True]


class PaperPoint(ResponseModel):
    date: str
    equity: float
    cash: float
    position_value: float
    position_weight: float
    enabled: bool


class LastPrice(ResponseModel):
    date: str
    close: float


class RiskLimits(ResponseModel):
    max_position_weight: float
    commission_bps: float
    slippage_bps: float
    minimum_fee: float


class PriceBar(ResponseModel):
    date: str
    symbol: str
    currency: Literal["EUR"]
    open: float
    high: float
    low: float
    close: float
    volume: float


class PaperAccount(ResponseModel):
    mode: Literal["paper"]
    currency: Literal["EUR"]
    initial_cash: float
    cash: float
    positions: dict[str, int]
    orders: list[PaperOrder]
    fills: list[PaperFill]
    last_processed_date: str
    started_at_date: str
    strategy: Strategy | None
    equity: float
    equity_curve: list[PaperPoint]
    last_price: float | None
    last_price_date: str | None
    last_prices: dict[str, LastPrice]
    observed_bars: list[PriceBar] | None = None
    warnings: list[str]
    enabled: bool
    risk_limits: RiskLimits | None = None


class ExperimentResponse(ResponseModel):
    id: str
    dataset_id: str
    dataset_version: int
    symbol: str
    prompt: str
    provider: Provider
    model: str | None
    budget_usd: float = Field(ge=0)
    hours: float
    auto_paper: bool
    costs: CostsResponse
    policy: PolicyResponse
    created_at: str
    status: ExperimentStatus
    phase: str
    cutoff: str
    frozen_hash: str
    spent_usd: float = Field(ge=0)
    reserved_usd: float = Field(ge=0)
    summary: Summary | None
    error: str | None
    observation: Observation
    gate: Gate | None
    paper_account: PaperAccount | None
    research: ResearchResult | None = None
    plan: Plan | None = None
    forward_result: BacktestResponse | None = None
    started_at: str | None = None
    observation_started_at: str | None = None
    finished_at: str | None = None
    completion_note: str | None = None
    resume_status: str | None = None
    restored_previous_status: str | None = None
    control_requested: Literal["pause", "cancel"] | None = None
    execution_active: bool = False
    execution_token: str | None = Field(default=None, exclude=True)


class PortfolioSummary(ResponseModel):
    id: str
    name: str
    revision: int


class StateResponse(ResponseModel):
    portfolios: list[PortfolioSummary] = Field(default_factory=list)
    datasets: list[DatasetResponse]
    experiments: list[ExperimentResponse]
    settings: SettingsResponse
    providers: list[ProviderResponse]
    audit: list[AuditEntry]
    server_time: str

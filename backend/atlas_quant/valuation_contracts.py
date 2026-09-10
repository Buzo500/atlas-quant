"""Typed NAV and provenance, separate from routine state and legacy snapshots."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .contracts import ResponseModel
from .multicurrency_contracts import NativeBalance

Status = Literal['complete', 'provisional', 'incomplete']


class Mark(ResponseModel):
    status: Status
    value: str | None
    series_id: str | None
    version: int | None
    sha256: str | None
    source: str | None
    date: str | None
    age_days: int | None
    available_at: str | None
    historical_known: bool
    reasons: list[str]
    historical_reasons: list[str]


class ValuationComponent(ResponseModel):
    kind: Literal['cash', 'position', 'receivable']
    reference: str
    currency: Literal['EUR', 'USD']
    quantity: str | None
    native_value: str | None
    eur_value: str | None
    display_eur: str | None
    status: Status
    price: Mark | None
    fx: Mark | None
    reasons: list[str]


class ExternalFlow(ResponseModel):
    event_id: str
    date: str
    currency: Literal['EUR', 'USD']
    native_amount: str
    eur_amount: str | None
    status: Status
    fx: Mark | None


class ValuationCut(ResponseModel):
    id: str
    portfolio_id: str
    portfolio_revision: int
    catalog_revision: int
    corporate_revision: int
    context_hash: str
    policy: Literal['atlas-nav-v1']
    mode: Literal['reconstruction_at_close']
    as_of_date: str
    decision_at: str
    created_at: str
    current: bool
    saved: bool
    status: Status
    value: str | None
    exact_value: str | None
    known_subtotal: str
    rounding_difference: str
    balance: NativeBalance
    components: list[ValuationComponent]
    flows: list[ExternalFlow]
    reasons: list[str]
    historical_known: bool
    historical_reasons: list[str]


class ValuationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    as_of_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    decision_at: str | None = Field(default=None, max_length=100)
    expected_revision: int = Field(ge=1)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class ValuationPreview(ResponseModel):
    cut: ValuationCut
    preview_token: str
    committed: bool


class ValuationSummary(ResponseModel):
    id: str
    as_of_date: str
    created_at: str
    portfolio_revision: int
    status: Status
    value: str | None


class ValuationHistory(ResponseModel):
    cuts: list[ValuationSummary]
    offset: int
    limit: int

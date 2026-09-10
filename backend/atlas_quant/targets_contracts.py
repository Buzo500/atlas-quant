"""Manual allocation percentages, reviewed activation and immutable diagnosis."""
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .contracts import ResponseModel
from .valuation_contracts import ValuationCut

Percent = Annotated[str, Field(pattern=r'^(?:0|[1-9]\d?|100)(?:\.\d{1,6})?$')]


class TargetRow(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    instrument_id: str | None = Field(default=None, pattern=r'^[0-9a-f]{32}$')
    weight: Percent
    minimum: Percent
    maximum: Percent
    concentration_limit: Percent

    @model_validator(mode='after')
    def coherent(self):
        if not (0 <= Decimal(self.minimum) <= Decimal(self.weight) <= Decimal(self.maximum)
                <= Decimal(self.concentration_limit) <= 100):
            raise ValueError('Se requiere mínimo ≤ objetivo ≤ máximo ≤ límite ≤ 100 %.')
        return self


class TargetSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    name: str = Field(min_length=1, max_length=120)
    rows: list[TargetRow] = Field(min_length=1, max_length=200)

    @model_validator(mode='after')
    def coherent(self):
        ids = [r.instrument_id for r in self.rows]
        if not self.name.strip():
            raise ValueError('Indica un nombre para los objetivos.')
        if len(ids) != len(set(ids)) or None not in ids:
            raise ValueError('Incluye efectivo y una sola fila por instrumento.')
        if sum((Decimal(r.weight) for r in self.rows), Decimal(0)) != 100:
            raise ValueError('Los objetivos deben sumar exactamente 100 %, incluido el efectivo.')
        return self


class TargetReview(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_revision: int = Field(ge=1)
    expected_targets_revision: int = Field(ge=0)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class TargetDraftInput(TargetReview):
    spec: TargetSpec


class TargetActivateInput(TargetReview):
    target_id: str = Field(pattern=r'^[0-9a-f]{64}$')


class TargetSet(ResponseModel):
    id: str
    portfolio_id: str
    version: int
    portfolio_revision: int
    catalog_revision: int
    created_at: str
    spec: TargetSpec


class TargetPreview(ResponseModel):
    target: TargetSet
    action: Literal['draft', 'activate']
    preview_token: str
    committed: bool


class TargetHistory(ResponseModel):
    revision: int
    active: TargetSet | None
    targets: list[TargetSet]
    offset: int
    limit: int


class TargetEvaluationInput(TargetReview):
    cut_id: str = Field(pattern=r'^[0-9a-f]{64}$')


class TargetExposure(ResponseModel):
    instrument_id: str | None
    label: str
    value_eur: str | None
    receivable_eur: str | None
    weight: str | None
    target_weight: str
    minimum: str | None
    maximum: str | None
    concentration_limit: str | None
    deviation_pp: str | None
    deviation_eur: str | None
    reasons: list[str]


class TargetCashResource(ResponseModel):
    currency: Literal['EUR', 'USD']
    native_amount: str | None
    eur_value: str | None


class TargetResources(ResponseModel):
    cash: list[TargetCashResource]
    committed: None
    reservation_status: Literal['not_implemented']


class TargetReport(ResponseModel):
    id: str
    portfolio_id: str
    created_at: str
    policy: Literal['atlas-targets-v1']
    context_hash: str
    current: bool
    saved: bool
    target: TargetSet
    cut: ValuationCut
    status: Literal['complete', 'provisional', 'unavailable']
    reasons: list[str]
    rows: list[TargetExposure]
    resources: TargetResources


class TargetReportPreview(ResponseModel):
    report: TargetReport
    preview_token: str
    committed: bool


class TargetReportSummary(ResponseModel):
    id: str
    portfolio_id: str
    created_at: str
    as_of_date: str
    target_version: int
    status: Literal['complete', 'provisional', 'unavailable']


class TargetReports(ResponseModel):
    reports: list[TargetReportSummary]
    offset: int
    limit: int

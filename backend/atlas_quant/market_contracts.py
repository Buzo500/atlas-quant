"""D6 market data contracts. Economic numbers cross HTTP as decimal strings."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from .contracts import ResponseModel
from .quality import EvidenceInput


class MarketImport(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=3, max_length=500)
    series_id: str | None = Field(default=None, min_length=1, max_length=100)
    expected_version: int = Field(default=0, ge=0)
    listing_id: str | None = Field(default=None, min_length=1, max_length=100)
    listing_ref: str = Field(default='ASSET', pattern=r'^[A-Z0-9][A-Z0-9_.:\-]{0,39}$')
    csv: str = Field(min_length=1, max_length=8_000_000)
    evidence: EvidenceInput | None = None
    revise_history: bool = False
    reason: str = Field(default='', max_length=500)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class MarketSeries(ResponseModel):
    id: str
    kind: Literal['prices', 'fx']
    name: str
    source: str
    version: int
    listing_id: str | None
    symbol: str
    currency: Literal['EUR', 'USD']
    format_id: Literal['atlas-prices-v2', 'atlas-fx-v1']
    sha256: str
    date_min: str
    date_max: str
    row_count: int
    received_at: str
    price_basis: str
    basis_verified: bool
    calendar_verified: bool


class MarketCatalog(ResponseModel):
    series: list[MarketSeries]


class MarketPreview(ResponseModel):
    series: MarketSeries
    added: int
    changed: int
    affected_portfolios: list[str]
    committed: bool
    preview_token: str


class MarketObservation(ResponseModel):
    date: str
    available_at: str | None
    open: str | None = None
    high: str | None = None
    low: str | None = None
    close: str | None = None
    volume: str | None = None
    rate: str | None = None


class MarketDetail(ResponseModel):
    series: MarketSeries
    evidence: dict[str, JsonValue]
    observations: list[MarketObservation]
    offset: int
    limit: int
    total: int


class FxBindingInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected_revision: int = Field(ge=1)
    series_id: str = Field(min_length=1, max_length=100)
    series_version: int = Field(ge=1)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')


class FxBinding(ResponseModel):
    portfolio_id: str
    portfolio_revision: int
    series_id: str | None
    series_version: int | None


class FxBindingPreview(FxBinding):
    committed: bool
    preview_token: str

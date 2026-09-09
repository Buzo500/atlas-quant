"""D2 API, separate from the v1 dataset/ledger wire contracts."""
from typing import Literal

from pydantic import Field, JsonValue

from .catalog import ExternalCode
from .contracts import ResponseModel, Position, PortfolioResponse, LedgerResponse
from .quality_contracts import QualityReport


class InstrumentResponse(ResponseModel):
    id: str
    name: str
    instrument_type: Literal["equity", "ETF", "unknown"]
    source: str
    verified: bool
    codes: list[ExternalCode]


class ListingResponse(ResponseModel):
    id: str
    instrument_id: str
    currency: Literal["EUR", "USD"]
    market: str | None
    calendar: str | None
    verified: bool
    legacy_dataset_id: str | None = None
    legacy_symbol: str | None = None


class AliasResponse(ResponseModel):
    id: str
    listing_id: str
    provider: str
    symbol: str
    valid_from: str | None
    valid_to: str | None
    source: str


class CatalogResponse(ResponseModel):
    revision: int
    instruments: list[InstrumentResponse]
    listings: list[ListingResponse]
    aliases: list[AliasResponse]


class PriceBinding(ResponseModel):
    listing_id: str = Field(min_length=1, max_length=100)
    dataset_id: str = Field(min_length=1, max_length=100)
    dataset_version: int = Field(ge=1, le=2_147_483_647)
    symbol: str = Field(min_length=1, max_length=50)


class PortfolioRecord(ResponseModel):
    id: str
    name: str
    account_id: str
    base_currency: Literal["EUR"]
    accounting_policy: Literal["legacy-eur-v1"]
    legacy_dataset_id: str | None
    revision: int
    catalog_revision: int
    event_ids: list[str]
    bindings: list[PriceBinding]


class IdentifiedPosition(Position):
    listing_id: str


class IdentifiedValue(PortfolioResponse):
    positions: list[IdentifiedPosition]


class PortfolioCut(ResponseModel):
    portfolio_id: str
    portfolio_revision: int
    catalog_revision: int
    accounting_policy: Literal["legacy-eur-v1"]
    bindings: list[PriceBinding]
    data_hash: str


class BookEntry(ResponseModel):
    event: dict[str, JsonValue]
    listing_id: str | None
    date: str
    day_sequence: int


class PortfolioDetail(ResponseModel):
    quality: list[QualityReport] = Field(default_factory=list)
    portfolio: PortfolioRecord
    context: PortfolioCut
    value: IdentifiedValue | None
    entries: list[BookEntry]
    status: Literal["available", "unavailable"]
    warnings: list[str]


class BindingPreview(PortfolioDetail):
    committed: bool
    preview_token: str = Field(pattern=r"^[0-9a-f]{64}$")


class PortfolioLedgerResponse(LedgerResponse):
    portfolio: IdentifiedValue

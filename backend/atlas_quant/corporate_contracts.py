"""Explicit D5 contracts. Strings are exact economic decimal values."""
from typing import Literal
from pydantic import Field, JsonValue
from .contracts import ResponseModel
from .book_contracts import Text, Note, ReviewInput, BookBalance, CorporateReview


class CorporateInput(ReviewInput):
    expected_revision: int = Field(ge=0)
    format_id: Literal["atlas-corporate-events-v1"]
    source: Text
    csv: str = Field(min_length=1, max_length=8_000_000)
    mapping: dict[Text, Text] = Field(default_factory=dict, max_length=100)
    event_mapping: dict[Text, Text] = Field(default_factory=dict, max_length=10_000)
    distinct_reasons: dict[Text, Note] = Field(default_factory=dict, max_length=10_000)
    verified: bool = False
    evidence: str = Field(default="", max_length=500)


class CorporateRevisionInput(ReviewInput):
    event_id: Text
    event_revision: int = Field(ge=1)
    action: Literal["replace", "cancel"]
    reason: Note
    csv: str = Field(default="", max_length=8_000_000)
    mapping: dict[Text, Text] = Field(default_factory=dict, max_length=100)
    verified: bool = False
    evidence: str = Field(default="", max_length=500)


class CorporateApplicationInput(ReviewInput):
    event_id: Text
    source: Text
    source_account: Text
    action: Literal["review", "cancel"] = "review"
    review: CorporateReview | None = None
    movement_id: Text | None = None
    reason: str = Field(default="", max_length=500)
    csv: str = Field(default="", max_length=8_000_000)


class CorporateEvent(ResponseModel):
    id: str
    revision: int
    listing_id: str
    event_type: Literal["dividend", "split"]
    effective_date: str | None
    payment_date: str | None
    available_at: str | None
    gross_per_unit: str | None
    currency: Literal["EUR"]
    ratio_numerator: int | None
    ratio_denominator: int | None
    source_reference: str
    verified: bool
    evidence: str
    cancelled: bool
    created_at: str
    reason: str


class CorporateSource(ResponseModel):
    source: str
    external_id: str
    event_id: str
    source_reference: str
    content_hash: str


class CorporateCatalog(ResponseModel):
    revision: int
    catalog_revision: int
    events: list[CorporateEvent]
    sources: list[CorporateSource]
    total: int
    offset: int
    limit: int


class CorporatePreview(CorporateCatalog):
    committed: bool
    preview_token: str
    document_id: str
    added: int
    duplicates: int


class CorporateApplication(ResponseModel):
    event_id: str
    event_revision: int
    revision: int
    portfolio_revision: int
    source: str
    source_account: str
    event_type: Literal["dividend", "split"]
    effective_date: str
    day_sequence: int
    eligible_quantity: str | None
    basis_quantity: str
    gross_amount: str | None
    movement_key: str | None
    movement_fingerprint: str | None
    basis_hash: str
    cancelled: bool
    evidence: str
    discrepancy_reason: str
    gross_explanation: str
    fraction_evidence: str
    event_snapshot: CorporateEvent
    current: bool
    status: Literal["pending_payment", "reconciled", "applied", "outdated", "cancelled"]
    receivable: str
    price_status: Literal["not_applicable", "compatible", "not_accredited"]
    warnings: list[str]


class CorporatePortfolio(ResponseModel):
    portfolio_id: str
    portfolio_revision: int
    corporate_revision: int
    as_of_date: str
    applications: list[CorporateApplication]
    balance: BookBalance
    pending_receivables: str
    unlinked_payments: list[str]
    warnings: list[str]
    total: int
    offset: int
    limit: int


class CorporateApplicationPreview(CorporatePortfolio):
    committed: bool
    preview_token: str
    document_id: str


class CorporateDocumentSummary(ResponseModel):
    id: str
    portfolio_id: str | None
    kind: str
    created_at: str


class CorporateDocument(CorporateDocumentSummary):
    evidence: dict[str, JsonValue]
    result: dict[str, JsonValue]


class CorporateDocuments(ResponseModel):
    documents: list[CorporateDocumentSummary]
    total: int
    offset: int
    limit: int

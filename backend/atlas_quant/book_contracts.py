"""Explicit D4 request/response contracts; decimal strings are economic values."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator
from .contracts import ResponseModel
from .identity_contracts import BookEntry

Text = Annotated[str, Field(min_length=1, max_length=100)]
Note = Annotated[str, Field(min_length=1, max_length=500)]


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    @field_validator("source", "source_account", "reason", mode="before", check_fields=False)
    @classmethod
    def trim_metadata(cls, value):
        return value.strip() if isinstance(value, str) else value
    expected_revision: int = Field(ge=1)
    commit: bool = False
    preview_token: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)


class CorporateReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    event_revision: int = Field(ge=1)
    day_sequence: int = Field(ge=1, le=999_999_999)
    evidence: Note
    eligible_quantity: str | None = Field(default=None, max_length=64)
    discrepancy_reason: str = Field(default="", max_length=500)
    gross_amount: str | None = Field(default=None, max_length=64)
    gross_explanation: str = Field(default="", max_length=500)
    fraction_evidence: str = Field(default="", max_length=500)


class ImportInput(ReviewInput):
    format_id: Literal["atlas-ledger-v2"]
    source: Text
    source_account: Text
    as_of_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    csv: str = Field(min_length=1, max_length=8_000_000)
    mapping: dict[Text, Text] = Field(default_factory=dict, max_length=100)
    gross_explanations: dict[Text, Note] = Field(default_factory=dict, max_length=10_000)
    corporate_mapping: dict[Text, Text] = Field(default_factory=dict, max_length=100)
    corporate_reviews: dict[Text, CorporateReview] = Field(default_factory=dict, max_length=100)
    unaccredited_payments: dict[Text, Note] = Field(default_factory=dict, max_length=10_000)


class ReconciliationInput(ReviewInput):
    format_id: Literal["atlas-statement-v2"]
    source: Text
    source_account: Text
    as_of_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    csv: str = Field(min_length=1, max_length=8_000_000)
    mapping: dict[Text, Text] = Field(default_factory=dict, max_length=100)
    complete_statement: Literal[True]


class CorrectionInput(ReviewInput):
    event_id: Text
    action: Literal["void", "replace"]
    reason: str = Field(min_length=3, max_length=500)
    csv: str = Field(default="", max_length=8_000_000)
    mapping: dict[Text, Text] = Field(default_factory=dict, max_length=100)
    gross_explanations: dict[Text, Note] = Field(default_factory=dict, max_length=10_000)
    corporate_mapping: dict[Text, Text] = Field(default_factory=dict, max_length=100)
    corporate_reviews: dict[Text, CorporateReview] = Field(default_factory=dict, max_length=100)
    unaccredited_payments: dict[Text, Note] = Field(default_factory=dict, max_length=10_000)


class BookPosition(ResponseModel):
    listing_id: str
    quantity: str
    cost_basis: str


class BookBalance(ResponseModel):
    as_of_date: str
    currency: Literal["EUR"]
    cash: str
    net_contributions: str
    realized_pnl: str | None
    positions: list[BookPosition]
    warnings: list[str]


class BookSource(ResponseModel):
    source: str
    source_account: str


class BookContext(ResponseModel):
    portfolio_id: str
    portfolio_revision: int
    catalog_revision: int
    accounting_policy: Literal["legacy-eur-v1", "atlas-accounting-v2"]
    as_of_date: str


class BookDetail(ResponseModel):
    context: BookContext
    balance: BookBalance
    entries: list[BookEntry]
    total: int
    offset: int
    limit: int
    sources: list[BookSource]


class BookPreview(BookDetail):
    added: int
    duplicates: int
    historical_insertion: bool
    committed: bool
    preview_token: str
    document_id: str


class ReconciliationRow(ResponseModel):
    record_type: Literal["cash", "position"]
    listing_id: str | None
    currency: Literal["EUR"]
    book: str
    reference: str
    difference: str
    matched: bool


class ReconciliationPreview(ResponseModel):
    context: BookContext
    balance: BookBalance
    status: Literal["matched", "differences"]
    differences: list[ReconciliationRow]
    total: int
    offset: int
    limit: int
    committed: bool
    preview_token: str
    document_id: str


class BookDocumentSummary(ResponseModel):
    id: str
    kind: Literal["import", "reconciliation", "correction"]
    portfolio_revision: int
    catalog_revision: int
    as_of_date: str
    source: str
    source_account: str
    created_at: str
    status: Literal["recorded", "matched", "differences"]
    added: int
    duplicates: int
    current: bool


class BookDocuments(ResponseModel):
    documents: list[BookDocumentSummary]
    total: int
    offset: int
    limit: int


class BookDocument(BookDocumentSummary):
    evidence: dict[str, JsonValue]
    balance: BookBalance
    differences: list[ReconciliationRow]


class BookIssue(ResponseModel):
    type: str
    msg: str
    loc: list[str | int]


class BookErrorResponse(ResponseModel):
    detail: list[BookIssue]

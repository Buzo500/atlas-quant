"""D6.1–D6.2 wire contracts. No EUR conversion or valuation is implied."""
from typing import Literal
from .contracts import ResponseModel
from .book_contracts import (BookPosition, BookDetail, BookPreview,
    ReconciliationPreview, ReconciliationRow, BookDocument)
from .corporate_contracts import (CorporateEvent, CorporateCatalog, CorporatePreview,
    CorporateApplication)

Currency = Literal['EUR', 'USD']


class NativeCash(ResponseModel):
    currency: Currency
    cash: str
    net_contributions: str
    realized_pnl: str | None


class NativePosition(BookPosition):
    currency: Currency


class NativeBalance(ResponseModel):
    as_of_date: str
    balances: list[NativeCash]
    positions: list[NativePosition]
    warnings: list[str]


class NativeBookDetail(BookDetail):
    balance: NativeBalance


class NativeBookPreview(BookPreview):
    balance: NativeBalance


class NativeReconciliationRow(ReconciliationRow):
    currency: Currency


class NativeReconciliationPreview(ReconciliationPreview):
    balance: NativeBalance
    differences: list[NativeReconciliationRow]


class NativeBookDocument(BookDocument):
    balance: NativeBalance
    differences: list[NativeReconciliationRow]


class NativeCorporateEvent(CorporateEvent):
    currency: Currency


class NativeCorporateCatalog(CorporateCatalog):
    events: list[NativeCorporateEvent]


class NativeCorporatePreview(CorporatePreview):
    events: list[NativeCorporateEvent]


class NativeCorporateApplication(CorporateApplication):
    event_snapshot: NativeCorporateEvent


class NativeReceivable(ResponseModel):
    currency: Currency
    amount: str


class NativeCorporatePortfolio(ResponseModel):
    portfolio_id: str
    portfolio_revision: int
    corporate_revision: int
    as_of_date: str
    applications: list[NativeCorporateApplication]
    balance: NativeBalance
    pending_receivables_by_currency: list[NativeReceivable]
    unlinked_payments: list[str]
    warnings: list[str]
    total: int
    offset: int
    limit: int


class NativeCorporateApplicationPreview(NativeCorporatePortfolio):
    committed: bool
    preview_token: str
    document_id: str

"""D6 API for bounded market reads, reviewed writes and saved valuation cuts."""
from typing import Literal
from fastapi import Query
from fastapi.responses import PlainTextResponse
from .market_contracts import MarketImport, MarketCatalog, MarketDetail, MarketPreview, FxBindingInput, FxBinding, FxBindingPreview
from .market_service import MarketService, PRICE_COLUMNS, FX_COLUMNS
from .valuation_contracts import ValuationInput, ValuationPreview, ValuationCut, ValuationHistory
from .valuation_service import ValuationService
from .book_contracts import BookErrorResponse


def register_market_routes(app, store):
    market, valuations = MarketService(store), ValuationService(store)
    errors = {422: {'model': BookErrorResponse}}

    @app.get('/api/v2/market', response_model=MarketCatalog)
    def catalog():
        return market.list()

    @app.get('/api/v2/market/{kind}/template', response_class=PlainTextResponse)
    def template(kind: Literal['prices', 'fx']):
        columns = PRICE_COLUMNS if kind == 'prices' else FX_COLUMNS
        example = '2026-01-05,ASSET,100,102,99,101,1000,USD,' if kind == 'prices' else '2026-01-05,USD,EUR,0.90,'
        return ','.join(columns)+'\n'+example+'\n'

    @app.post('/api/v2/market/{kind}/imports', response_model=MarketPreview, responses=errors)
    def imports(kind: Literal['prices', 'fx'], body: MarketImport):
        return market.import_series(kind, body)

    @app.get('/api/v2/market/{kind}/{ident}/versions/{version}', response_model=MarketDetail)
    def observations(kind: Literal['prices', 'fx'], ident: str, version: int, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return market.read(kind, ident, version, offset, limit)

    @app.get('/api/v2/portfolios/{ident}/fx-binding', response_model=FxBinding)
    def binding(ident: str, revision: int | None = Query(None, ge=1)):
        return market.fx_binding(ident, revision)

    @app.post('/api/v2/portfolios/{ident}/fx-binding', response_model=FxBindingPreview)
    def bind(ident: str, body: FxBindingInput):
        return market.bind_fx(ident, body)

    @app.post('/api/v2/portfolios/{ident}/valuations', response_model=ValuationPreview, responses=errors)
    def value(ident: str, body: ValuationInput):
        return valuations.calculate(ident, body)

    @app.get('/api/v2/portfolios/{ident}/valuations', response_model=ValuationHistory)
    def history(ident: str, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
        return valuations.history(ident, offset, limit)

    @app.get('/api/v2/portfolios/{ident}/valuations/{cut_id}', response_model=ValuationCut)
    def cut(ident: str, cut_id: str):
        return valuations.read(ident, cut_id)

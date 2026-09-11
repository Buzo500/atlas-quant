from fastapi import Query
from .asset_analysis_contracts import AssetAnalysisInput, AssetAnalysisPreview, AssetAnalysisHistory, AssetAnalysisReport, AssetSourceCatalog
from .asset_analysis_service import AssetAnalysisService


def register_asset_analysis_routes(app,store):
    service=AssetAnalysisService(store)

    @app.get('/api/v2/asset-analysis/sources',response_model=AssetSourceCatalog)
    def sources():
        return service.catalog()

    @app.post('/api/v2/asset-analysis/reports',response_model=AssetAnalysisPreview)
    def calculate(body: AssetAnalysisInput):
        return service.calculate(body)

    @app.get('/api/v2/asset-analysis/reports',response_model=AssetAnalysisHistory)
    def history(offset: int=Query(0,ge=0),limit: int=Query(20,ge=1,le=100)):
        return service.history(offset,limit)

    @app.get('/api/v2/asset-analysis/reports/{ident}',response_model=AssetAnalysisReport)
    def report(ident: str):
        return service.report(ident)

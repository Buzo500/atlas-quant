from fastapi import Query
from .planning_contracts import PlanningInput, PlanningPreview, PlanningHistory, PlanningReport
from .planning_service import PlanningService


def register_planning_routes(app,store):
    service=PlanningService(store)

    @app.post('/api/v2/portfolios/{ident}/planning-reports',response_model=PlanningPreview)
    def calculate(ident: str,body: PlanningInput):
        return service.calculate(ident,body)

    @app.get('/api/v2/portfolios/{ident}/planning-reports',response_model=PlanningHistory)
    def history(ident: str,offset: int=Query(0,ge=0),limit: int=Query(20,ge=1,le=100)):
        return service.history(ident,offset,limit)

    @app.get('/api/v2/portfolios/{ident}/planning-reports/{report_id}',response_model=PlanningReport)
    def report(ident: str,report_id: str):
        return service.report(ident,report_id)

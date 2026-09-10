"""Analytical use cases: coherent snapshots, bounded calculation and atomic history."""
import hmac
from . import planning
from .catalog import IdentityNotFound, RevisionConflict
from .computation import bounded_calculation
from .portfolios import fingerprint, PortfolioService
from .targets_service import TargetsService, utc
from .valuation import MarkSeries, missing


class PlanningService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def signature(work, ident):
        return TargetsService.evaluation_stamp(work, ident)

    @bounded_calculation
    def calculate(self, ident, body):
        def read(work):
            context = TargetsService.context(work, ident)
            TargetsService.revision(context, body)
            active = work.target_set(ident, context['head']['active_id'])
            if body.kind != 'benchmark' and active is None:
                raise ValueError('Activa objetivos globales antes de planificar o evaluar límites.')
            contributors = []
            for s in body.strategies:
                target = work.target_set(ident, s.target_id)
                if target is None:
                    raise IdentityNotFound('Objetivos de estrategia no encontrados en esta cartera.')
                contributors.append(dict(target=target,budget=s.budget))
            cut = work.valuation(ident, body.cut_id) if body.cut_id else None
            performance = work.performance(ident, body.performance_id) if body.performance_id else None
            if body.kind in ('allocation','scenario') and cut is None:
                raise IdentityNotFound('Corte no encontrado en esta cartera.')
            if body.kind == 'benchmark' and performance is None:
                raise IdentityNotFound('Informe de rentabilidad no encontrado en esta cartera.')
            stamp = fingerprint(work.valuation_stamp(ident))
            for value in (cut, performance):
                if value and value['context_hash'] != stamp:
                    raise RevisionConflict('La fuente analítica está obsoleta. Calcula y guarda un informe vigente.')
            sources = PortfolioService._context(work, ident, include_entries=False) if body.kind=='allocation' else None
            fx_binding = work.portfolio_fx(ident,context['portfolio']['revision']) if sources else None
            fx = work.market_version('fx',fx_binding['series_id'],fx_binding['series_version']) if fx_binding else None
            return context,active,contributors,cut,performance,work.corporate_state(),sources,fx,self.signature(work,ident)
        context,active,contributors,cut,performance,corporate,sources,fx,signature = self.store.read(read)
        combined = planning.combine(active,contributors) if contributors and body.kind in ('allocation','aggregate') else None
        if combined:
            combined['labels'] = {i['id']: i['name'] for i in context['catalog']['instruments'] if any(r['instrument_id']==i['id'] for r in combined['spec']['rows'])}
        if body.kind == 'aggregate':
            result = dict(kind='aggregate',combined=combined)
        elif body.kind == 'scenario':
            result = planning.scenario(cut,active,context['catalog'],corporate,body)
        elif body.kind == 'benchmark':
            result = planning.benchmark(performance,body)
        else:
            data = {(d['id'],d['version']): d for d in sources['datasets']}
            prices = {}
            chosen = {r.listing_id for r in body.rules}
            for b in context['portfolio']['bindings']:
                if b['listing_id'] in chosen and (b['dataset_id'],b['dataset_version']) in data:
                    series = MarkSeries(data[(b['dataset_id'],b['dataset_version'])],b['symbol'])
                    prices[b['listing_id']] = dict(price=series.select(cut['as_of_date'],cut['decision_at']))
            fx_mark = MarkSeries(fx,'USD_EUR','fx').select(cut['as_of_date'],cut['decision_at']) if fx else missing('missing_fx')
            result = planning.allocation(cut,active,combined,context['catalog'],corporate,body,dict(prices=prices,fx=fx_mark))
        inputs = body.model_dump(exclude={'commit','preview_token'})
        token = fingerprint(dict(policy=planning.POLICY,context=signature,inputs=inputs))
        report = dict(id=token,portfolio_id=ident,created_at=utc(),policy=planning.POLICY,context_hash=signature,
            current=True,saved=body.commit,inputs=dict(inputs,commit=False,preview_token=None),result=result)

        def publish(work):
            if self.signature(work,ident)!=signature or work.targets_head(ident)['revision']!=body.expected_targets_revision:
                raise RevisionConflict('El contexto cambió durante el análisis. Vuelve a previsualizar.')
            if body.commit:
                if not body.preview_token or not hmac.compare_digest(token,body.preview_token):
                    raise RevisionConflict('Previsualización ausente u obsoleta.')
                old = work.planning_report(ident,token)
                if old: return old
                work.save_planning(report)
                work.audit('planning.saved',ident,dict(report_id=token,kind=body.kind,context_hash=signature))
            return report
        return dict(report=self.store.atomic(publish),preview_token=token,committed=body.commit)

    def history(self,ident,offset=0,limit=20):
        def read(work):
            TargetsService.context(work,ident)
            return dict(reports=work.planning_history(ident,offset,limit),offset=offset,limit=limit)
        return self.store.read(read)

    def report(self,ident,report_id):
        def read(work):
            TargetsService.context(work,ident)
            value = work.planning_report(ident,report_id)
            if value is None: raise IdentityNotFound('Análisis no encontrado.')
            current = value['context_hash']==self.signature(work,ident)
            result = dict(value['result'])
            if 'cut' in result: result['cut']=dict(result['cut'],current=current)
            return dict(value,current=current,result=result)
        return self.store.read(read)

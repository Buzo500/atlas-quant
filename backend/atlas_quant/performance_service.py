"""Period calculation shares D6's coherent context and optimistic publication."""
from datetime import datetime, timezone
import hmac
from . import performance
from .book_service import BookService
from .catalog import IdentityNotFound, RevisionConflict
from .portfolios import fingerprint
from .valuation_service import ValuationService
from .computation import bounded_calculation


class PerformanceService:
    def __init__(self, store):
        self.store = store

    @bounded_calculation
    def calculate(self, ident, body):
        context = self.store.read(lambda w: ValuationService.context(w, ident))
        BookService._revision(context, body.expected_revision)
        signature = ValuationService.signature(context)
        report = performance.calculate(context, body.start_date, body.end_date)
        token = fingerprint(dict(context=signature, policy=performance.POLICY,
            body=body.model_dump(exclude={'commit','preview_token'})))
        report.update(id=token, portfolio_id=ident, portfolio_revision=context['portfolio']['revision'],
            context_hash=signature, created_at=datetime.now(timezone.utc).isoformat(), current=True, saved=body.commit)
        def publish(work):
            if fingerprint(work.valuation_stamp(ident)) != signature:
                raise RevisionConflict('El contexto cambió durante el cálculo; vuelve a previsualizar.')
            if body.commit:
                if not body.preview_token or not hmac.compare_digest(body.preview_token, token):
                    raise RevisionConflict('Previsualización de rentabilidad ausente u obsoleta.')
                old = work.performance(ident, token)
                if old:
                    return old
                work.save_performance(report)
                work.audit('performance.saved', ident, dict(report_id=token, context_hash=signature,
                    start_date=body.start_date, end_date=body.end_date))
            return report
        return dict(report=self.store.atomic(publish), preview_token=token, committed=body.commit)

    def read(self, ident, report_id):
        def read(work):
            value = work.performance(ident, report_id)
            if value is None:
                raise IdentityNotFound('Informe de rentabilidad no encontrado.')
            return dict(value, current=fingerprint(work.valuation_stamp(ident)) == value['context_hash'])
        return self.store.read(read)

    def history(self, ident, offset=0, limit=20):
        return dict(reports=self.store.read(lambda w:w.performance_history(ident,offset,limit)), offset=offset, limit=limit)

"""Coherent snapshots and immutable NAV publication with optimistic validation."""
from datetime import datetime, timezone
import hmac

from .book import POLICY, cutoff
from .book_service import BookService
from .catalog import IdentityNotFound, RevisionConflict
from .portfolios import fingerprint, PortfolioService
from .valuation import Valuator


class ValuationService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def context(work, ident, revision=None):
        result = BookService._context(work, ident, revision)
        if result['portfolio']['accounting_policy'] != POLICY:
            raise ValueError('La valoración nativa requiere libro v2; la cartera heredada conserva su resultado.')
        # The existing binding validator enforces both currency and native identity.
        prices = PortfolioService._context(work, ident, revision, include_entries=False)
        result['datasets'] = prices['datasets']
        result['fx_binding'] = work.portfolio_fx(ident, result['portfolio']['revision'])
        binding = result['fx_binding']
        result['fx'] = work.market_version('fx', binding['series_id'], binding['series_version']) if binding else None
        result['stamp'] = work.valuation_stamp(ident, revision)
        return result

    @staticmethod
    def signature(context):
        return fingerprint(context['stamp'])

    def calculate(self, ident, body):
        day = cutoff(body.as_of_date)
        context = self.store.read(lambda w: self.context(w, ident))
        BookService._revision(context, body.expected_revision)
        signature = self.signature(context)
        value = Valuator(context).cut(day, body.decision_at)
        token = fingerprint(dict(context=signature, body=body.model_dump(exclude={'commit', 'preview_token'}), policy='atlas-nav-v1'))
        value.update(id=token, portfolio_id=ident, portfolio_revision=context['portfolio']['revision'],
            catalog_revision=context['catalog']['revision'], corporate_revision=context['corporate']['revision'], context_hash=signature,
            created_at=datetime.now(timezone.utc).isoformat(), current=True, saved=body.commit)
        def verify(work):
            if fingerprint(work.valuation_stamp(ident)) != signature:
                raise RevisionConflict('El contexto cambió durante la valoración. Calcula de nuevo.')
            if body.commit:
                if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
                    raise RevisionConflict('La previsualización del patrimonio está obsoleta o ausente.')
                old = work.valuation(ident, token)
                if old:
                    return old
                work.save_valuation(value)
                work.audit('valuation.saved', ident, dict(cut_id=token, context_hash=signature, as_of_date=day))
            return value
        value = self.store.atomic(verify)
        return dict(cut=value, committed=body.commit, preview_token=token)

    def read(self, ident, cut_id):
        def read(work):
            value = work.valuation(ident, cut_id)
            if value is None:
                raise IdentityNotFound('Corte de patrimonio no encontrado.')
            return {**value, 'current': fingerprint(work.valuation_stamp(ident)) == value['context_hash']}
        return self.store.read(read)

    def history(self, ident, offset=0, limit=100):
        values = self.store.read(lambda w: w.valuations(ident, offset, limit))
        return dict(cuts=[{k: v[k] for k in ('id', 'as_of_date', 'created_at', 'portfolio_revision', 'status', 'value')} for v in values], offset=offset, limit=limit)

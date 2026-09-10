"""Versioned manual objectives; coherent review, CAS activation, immutable analysis."""
from datetime import datetime, timezone
import hmac
from . import targets
from .book import POLICY
from .catalog import IdentityNotFound, RevisionConflict
from .portfolios import fingerprint
from .computation import bounded_calculation


def utc():
    return datetime.now(timezone.utc).isoformat()


class TargetsService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def context(work, ident):
        try:
            portfolio = work.portfolio_record(ident)
        except KeyError as exc:
            raise IdentityNotFound('Cartera no encontrada.') from exc
        if portfolio['accounting_policy'] != POLICY:
            raise ValueError('Los objetivos requieren una cartera con libro v2; se conserva la política heredada.')
        return dict(portfolio=portfolio, catalog=work.catalog(), head=work.targets_head(ident))

    @staticmethod
    def stamp(context):
        return dict(portfolio_revision=context['portfolio']['revision'],
            catalog_revision=context['catalog']['revision'], targets_revision=context['head']['revision'])

    @staticmethod
    def current_stamp(work, ident):
        return dict(portfolio_revision=work.portfolio_record(ident)['revision'],
            catalog_revision=work.db.execute('SELECT COALESCE(MAX(revision),0) FROM catalog_revisions').fetchone()[0],
            targets_revision=work.targets_head(ident)['revision'])

    @staticmethod
    def revision(context, body):
        if (context['portfolio']['revision'] != body.expected_revision or
                context['head']['revision'] != body.expected_targets_revision):
            raise RevisionConflict('El libro o los objetivos han cambiado. Actualiza y vuelve a previsualizar.')

    @staticmethod
    def validate(spec, catalog):
        available = {i['id'] for i in catalog['instruments']}
        if any(r['instrument_id'] is not None and r['instrument_id'] not in available for r in spec['rows']):
            raise ValueError('El objetivo referencia un instrumento inexistente.')

    def review(self, ident, body, action):
        def read(work):
            context = self.context(work, ident)
            target = work.target_set(ident, body.target_id) if action == 'activate' else None
            return context, target
        context, target = self.store.read(read)
        self.revision(context, body)
        if action == 'activate' and target is None:
            raise IdentityNotFound('Borrador de objetivos no encontrado en esta cartera.')
        spec = body.spec.model_dump() if action == 'draft' else target['spec']
        self.validate(spec, context['catalog'])
        stamp = self.stamp(context)
        token = fingerprint(dict(portfolio_id=ident, action=action, context=stamp,
            body=body.model_dump(exclude={'commit', 'preview_token'}), policy=targets.POLICY))
        if action == 'draft':
            target = dict(id=token, portfolio_id=ident, version=context['head']['next_version'],
                portfolio_revision=context['portfolio']['revision'], catalog_revision=context['catalog']['revision'],
                created_at=utc(), spec=spec)
        def publish(work):
            if self.current_stamp(work, ident) != stamp:
                raise RevisionConflict('El contexto cambió durante la revisión de objetivos.')
            if body.commit:
                if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
                    raise RevisionConflict('Previsualización de objetivos ausente u obsoleta.')
                old_head = work.targets_head(ident)
                head = dict(old_head, revision=old_head['revision']+1)
                if action == 'draft':
                    work.insert_target_record('target_set', target)
                    head['next_version'] += 1
                else:
                    head['active_id'] = target['id']
                work.put('targets_head', head)
                work.audit('targets.'+action, ident, dict(target_id=target['id'], version=target['version'],
                    previous_active_id=old_head['active_id'], targets_revision=head['revision']))
            return dict(target=target, action=action, preview_token=token, committed=body.commit)
        return self.store.atomic(publish)

    def history(self, ident, offset=0, limit=20):
        def read(work):
            context = self.context(work, ident)
            head = context['head']
            return dict(revision=head['revision'], active=work.target_set(ident, head['active_id']),
                targets=work.target_history('target_set', ident, offset, limit), offset=offset, limit=limit)
        return self.store.read(read)

    @staticmethod
    def evaluation_stamp(work, ident):
        return fingerprint(dict(valuation=work.valuation_stamp(ident), active_id=work.targets_head(ident)['active_id']))

    @bounded_calculation
    def evaluate(self, ident, body):
        def read(work):
            context = self.context(work, ident)
            self.revision(context, body)
            target = work.target_set(ident, context['head']['active_id'])
            cut = work.valuation(ident, body.cut_id)
            if target is None:
                raise ValueError('Activa un conjunto de objetivos antes de evaluar.')
            if cut is None:
                raise IdentityNotFound('Selecciona un corte de patrimonio guardado de esta cartera.')
            if cut['context_hash'] != fingerprint(work.valuation_stamp(ident)):
                raise RevisionConflict('El corte está obsoleto. Calcula y guarda un corte vigente.')
            return context, target, cut, work.corporate_state(), self.evaluation_stamp(work, ident)
        context, target, cut, corporate, signature = self.store.read(read)
        value = targets.evaluate(cut, target['spec'], context['catalog'], corporate)
        token = fingerprint(dict(context=signature, cut_id=cut['id'], policy=targets.POLICY))
        value.update(id=token, portfolio_id=ident, created_at=utc(), context_hash=signature,
            current=True, saved=body.commit, target=target, cut=cut)
        def publish(work):
            current = self.current_stamp(work, ident)
            if current['portfolio_revision'] != body.expected_revision or current['targets_revision'] != body.expected_targets_revision:
                raise RevisionConflict('El libro o los objetivos cambiaron durante el diagnóstico.')
            if self.evaluation_stamp(work, ident) != signature:
                raise RevisionConflict('El contexto cambió durante el diagnóstico. Vuelve a previsualizar.')
            if body.commit:
                if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
                    raise RevisionConflict('Previsualización de diagnóstico ausente u obsoleta.')
                old = work.target_report(ident, token)
                if old:
                    return old
                work.insert_target_record('target_report', value)
                work.insert_target_record('target_report_summary', dict(id=token, portfolio_id=ident,
                    created_at=value['created_at'], as_of_date=cut['as_of_date'], target_version=target['version'], status=value['status']))
                work.audit('targets.evaluated', ident, dict(report_id=token, target_id=target['id'], cut_id=cut['id']))
            return value
        return dict(report=self.store.atomic(publish), preview_token=token, committed=body.commit)

    def reports(self, ident, offset=0, limit=20):
        def read(work):
            self.context(work, ident)
            return dict(reports=work.target_history('target_report_summary', ident, offset, limit), offset=offset, limit=limit)
        return self.store.read(read)

    def report(self, ident, report_id):
        def read(work):
            self.context(work, ident)
            value = work.target_report(ident, report_id)
            if value is None:
                raise IdentityNotFound('Diagnóstico no encontrado.')
            current = value['context_hash'] == self.evaluation_stamp(work, ident)
            return dict(value, current=current, cut=dict(value['cut'], current=value['cut']['context_hash'] == fingerprint(work.valuation_stamp(ident))))
        return self.store.read(read)

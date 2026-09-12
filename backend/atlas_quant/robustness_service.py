"""Separate immutable statistical reports, with a development-only storage boundary."""
import platform
from .catalog import IdentityNotFound, RevisionConflict
from .computation import bounded_calculation
from .quality import digest
from .robustness import evaluate
from .robustness_contracts import POLICY
from .store import now


def trial_context(value):
    p = value['protocol']
    context = {k: p[k] for k in ('policy', 'instrument_id', 'listing_id', 'series_id', 'series_version',
        'source_hash', 'start_date', 'holdout_date', 'end_date')}
    context.update(config=value['config'], evidence_hash=value['evidence_hash'])
    return dict(protocol_id=p['id'], name=p['name'], development_hash=value['development']['report_hash'],
                source_hash=p['source_hash'], context_hash=digest(context))


class RobustnessService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _get(work, ident):
        record = work.get('robustness_report', ident)
        if record is None:
            raise IdentityNotFound('Informe estadístico no encontrado.')
        return record

    @staticmethod
    def _snapshot(work, body):
        revision = work.robustness_candidate(body.candidate_id, body.revision)
        if revision is None:
            raise IdentityNotFound('Revisión de candidata no encontrada.')
        if revision['revision_hash'] != body.revision_hash:
            raise RevisionConflict('La huella no coincide con la revisión elegida. Revisa la evidencia.')
        if set(body.related_protocol_ids) != set(revision['protocol_ids']):
            raise ValueError('Declara todos los protocolos vinculados a esta revisión; no omitas evidencia previa.')
        references = {v['protocol_id']: v['development_hash'] for v in revision['evidence']}
        main, trials = None, []
        for ident in body.related_protocol_ids:
            value = work.robustness_development(ident)
            if value is None:
                raise IdentityNotFound('Protocolo relacionado no encontrado.')
            if references.get(ident) != value['development']['report_hash']:
                raise RevisionConflict('El desarrollo no coincide con la evidencia capturada por la candidata.')
            trials.append(trial_context(value))
            if ident == body.protocol_id:
                main = value
        return dict(development=main, trials=trials, revision_hash=revision['revision_hash'])

    def history(self, candidate, offset=0, limit=20):
        return dict(items=self.store.read(lambda w: w.robustness_history(candidate, offset, limit)), offset=offset, limit=limit)

    def read(self, ident):
        return self.store.read(lambda w: self._get(w, ident)['report'])

    @bounded_calculation
    def create(self, body):
        snapshot = self.store.read(lambda w: self._snapshot(w, body))
        signature = digest(snapshot)
        request = body.model_dump(mode='json')
        ident = digest(dict(policy=POLICY, request=request, snapshot_hash=signature))
        prior = self.store.read(lambda w: w.get('robustness_report', ident))
        if prior:
            return prior['report']
        main = snapshot['development']
        result = evaluate(main)
        report = dict(id=ident, created_at=now(), request=request, protocol=main['protocol'], config=main['config'],
            metrics=main['development']['metrics'], rejected=main['development']['rejected'],
            expired=main['development']['expired'], trials=snapshot['trials'], snapshot_hash=signature,
            result=result, python_version=platform.python_version(), platform=platform.system() + '-' + platform.machine())
        report['report_hash'] = digest(report)
        def save(work):
            if digest(self._snapshot(work, body)) != signature:
                raise RevisionConflict('Cambió el contexto durante el cálculo. Revisa la consulta antes de guardar.')
            previous = work.get('robustness_report', ident)
            if previous:
                return previous['report']
            work.lab_insert('robustness_report', dict(id=ident, report=report, snapshot=snapshot))
            work.audit('lab.robustness_saved', ident, dict(policy=POLICY, report_hash=report['report_hash'],
                candidate_id=body.candidate_id, revision=body.revision, status=result['status']))
            return report
        return self.store.atomic(save)

    @bounded_calculation
    def reproduce(self, ident):
        record = self.store.read(lambda w: self._get(w, ident))
        report, snapshot = record['report'], record['snapshot']
        actual = evaluate(snapshot['development'])
        snapshot_matches = digest(snapshot) == report['snapshot_hash']
        result_matches = actual == report['result']
        environment_matches = (report['python_version'] == platform.python_version() and
            report['platform'] == platform.system() + '-' + platform.machine())
        report_matches = digest({k: v for k, v in report.items() if k != 'report_hash'}) == report['report_hash']
        return dict(id=ident, matches=snapshot_matches and result_matches and report_matches,
            snapshot_matches=snapshot_matches, result_matches=result_matches, environment_matches=environment_matches,
            warnings=[] if environment_matches else ['Entorno distinto del registrado; no se presupone igualdad binaria entre equipos.'])

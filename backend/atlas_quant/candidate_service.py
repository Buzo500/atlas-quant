"""Transactional, optimistic research registry with immutable report references."""
from .candidate_contracts import CANDIDATE_POLICY
from .catalog import IdentityNotFound, RevisionConflict
from .quality import digest
from .store import now


class CandidateService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _current(work, ident):
        summary = work.get('candidate_summary', ident)
        if summary is None:
            raise IdentityNotFound('Candidata no encontrada.')
        return work.get('candidate_revision', f"{ident}:{summary['revision']}")

    def history(self, offset=0, limit=20):
        return dict(items=self.store.read(lambda w: w.candidate_history(offset, limit)), offset=offset, limit=limit)

    def read(self, ident):
        return self.store.read(lambda w: self._current(w, ident))

    def revisions(self, ident, offset=0, limit=20):
        def read(work):
            self._current(work, ident)
            return work.candidate_revisions(ident, offset, limit)
        return dict(items=self.store.read(read), offset=offset, limit=limit)

    @staticmethod
    def _revision(work, ident, body, prior=None):
        old_ids = set(prior['protocol_ids']) if prior else set()
        if not old_ids.issubset(body.protocol_ids):
            raise ValueError('No se puede eliminar evidencia vinculada; conserva los informes y explica el descarte.')
        timestamp = now()
        # Only a deliberate new revision captures newly available evidence;
        # previous revisions keep their original snapshots byte for byte.
        evidence = []
        for protocol_id in body.protocol_ids:
            value = work.get('lab_protocol', protocol_id)
            if value is None:
                raise IdentityNotFound('Uno de los protocolos no existe.')
            evidence.append(dict(protocol=value['protocol'], captured_at=timestamp,
                development_hash=value['development']['report_hash'], development_metrics=value['development']['metrics'],
                walk_forward_hash=value.get('walk_forward', {}).get('report_hash'),
                sensitivity_hash=value.get('sensitivity', {}).get('report_hash'),
                holdout_hash=value['holdout']['report_hash'] if value['holdout'] else None,
                holdout_metrics=value['holdout']['metrics'] if value['holdout'] else None))
        revision = prior['revision'] + 1 if prior else 1
        value = dict(id=f'{ident}:{revision}', candidate_id=ident, revision=revision,
            **body.model_dump(mode='json', exclude={'expected_revision'}), created_at=timestamp,
            policy=CANDIDATE_POLICY, evidence=sorted(evidence, key=lambda e: e['protocol']['id']))
        value['revision_hash'] = digest(value)
        work.lab_insert('candidate_revision', value)
        work.put('candidate_summary', dict(id=ident, name=body.name, revision=revision, status=body.status,
            updated_at=timestamp, protocols=len(body.protocol_ids)))
        work.audit('candidate.revised' if prior else 'candidate.created', ident,
            dict(revision=revision, revision_hash=value['revision_hash'], status=body.status))
        return value

    def create(self, body):
        ident = digest(dict(policy=CANDIDATE_POLICY, initial=body.model_dump(mode='json')))
        def save(work):
            # A repeated create returns its original revision, never a silently changed draft.
            old = work.get('candidate_revision', f'{ident}:1')
            return old if old else self._revision(work, ident, body)
        return self.store.atomic(save)

    def revise(self, ident, body):
        def save(work):
            prior = self._current(work, ident)
            if prior['revision'] != body.expected_revision:
                raise RevisionConflict('La candidata cambió. Consulta su revisión actual antes de volver a guardar.')
            if prior['revision'] >= 100:
                raise ValueError('Máximo cien revisiones por candidata.')
            return self._revision(work, ident, body, prior)
        return self.store.atomic(save)

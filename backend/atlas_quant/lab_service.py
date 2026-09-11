"""Frozen protocols, durable temporal reservations and atomic result publication."""
from .catalog import IdentityNotFound, RevisionConflict
from .computation import bounded_calculation
from .lab_contracts import LabInput, POLICY
from .lab_sources import freeze_source
from .lab_economics import period
from .walk_forward import evaluate as walk_forward, plan as plan_walk_forward
from .sensitivity import evaluate as sensitivity, plan as plan_sensitivity
from .quality import digest
from .store import now

WARNINGS = [
    'Simulación aislada EUR; no envía órdenes ni modifica carteras.',
    'Evidencia declarada y revisada por el usuario; ATLAS comprueba su coherencia, no certifica su origen.',
    'Desarrollo y prueba final empiezan en efectivo, con calentamiento SMA independiente. Comprar/mantener intenta entrar en la primera apertura.',
    'NAV al precio de cierre cuando está disponible antes de la apertura siguiente; sin liquidación forzada al terminar.',
    'La reserva protege frente a simulaciones de este Laboratorio y esta base, no frente a datos vistos en otros análisis o fuera de ATLAS.',
    'No es una validación completa: faltan walk-forward, sensibilidad y pruebas de sobreajuste.'
]


class LabService:
    def __init__(self, store):
        self.store = store

    def history(self, offset=0, limit=20):
        return dict(items=self.store.read(lambda w: w.lab_history(offset, limit)), offset=offset, limit=limit)

    @staticmethod
    def _get(work, ident):
        value = work.get('lab_protocol', ident)
        if value is None:
            raise IdentityNotFound('Protocolo de Laboratorio no encontrado.')
        return value

    @staticmethod
    def _public(value):
        result = {k: value[k] for k in ('protocol', 'config', 'development', 'holdout', 'warnings', 'evidence_hash')}
        for name in ('walk_forward', 'sensitivity'):
            if name in value:
                result[name] = value[name]
        return result

    def read(self, ident):
        return self._public(self.store.read(lambda w: self._get(w, ident)))

    @staticmethod
    def _snapshot(work, body):
        size = work.analysis_version_size(body.series_id, body.series_version)
        if size is None:
            raise IdentityNotFound('Versión nativa no encontrada.')
        if size > 100_000:
            raise ValueError('La fuente supera 100.000 barras; importa una serie acotada.')
        data = work.market_version('prices', body.series_id, body.series_version)
        if not data or data.get('format_id') != 'atlas-prices-v2':
            raise ValueError('Selecciona una versión CSV nativa, no una serie heredada.')
        listing = next((l for l in work.catalog()['listings'] if l['id'] == data['listing_id']), None)
        if listing is None:
            raise IdentityNotFound('Cotización no encontrada.')
        return data, listing, work.corporate_state()

    @staticmethod
    def _guard(work, summary, opening=False):
        instrument = summary['instrument_id']
        if work.lab_overlaps('lab_exposure', instrument, summary['holdout_date'], summary['end_date']):
            raise RevisionConflict('La prueba final coincide con un periodo ya calculado en este Laboratorio. Elige datos nuevos.')
        if not opening:
            # Compare against the last actual development session, not a calendar-day subtraction.
            end = summary['development_end']
            if work.lab_reserved(instrument, summary['start_date'], end, summary['id']):
                raise RevisionConflict('El desarrollo invade una prueba final reservada por otro protocolo.')

    @bounded_calculation
    def create(self, body):
        snapshot = self.store.read(lambda w: self._snapshot(w, body))
        frozen = freeze_source(*snapshot, body)
        inputs = body.model_dump(mode='json', exclude={name for name in ('walk_forward', 'sensitivity') if getattr(body, name) is None})
        ident = digest(dict(policy=POLICY, inputs=inputs, frozen=frozen))
        prior = self.store.read(lambda w: w.get('lab_protocol', ident))
        if prior:
            return self._public(prior)
        source = frozen['source']
        summary = dict(id=ident, name=body.name, created_at=now(), policy=POLICY,
            instrument_id=source['instrument_id'], listing_id=source['listing_id'], series_id=source['id'],
            series_version=source['version'], source_hash=source['sha256'], start_date=body.start_date,
            holdout_date=body.holdout_date, end_date=body.end_date, opened=False, fast=body.fast, slow=body.slow)
        guard = dict(summary, development_end=max(s['date'] for s in frozen['calendar']['sessions'] if s['date'] < body.holdout_date))
        self.store.read(lambda w: self._guard(w, guard))
        if body.walk_forward is not None:
            plan_walk_forward(frozen['calendar']['sessions'], body)
        if body.sensitivity is not None:
            plan_sensitivity(body, frozen['calendar']['sessions'])
        development = period(frozen, body, False)
        value = dict(id=ident, protocol=summary, inputs=inputs, frozen=frozen,
            config=body.config.model_dump(mode='json'), development=development, holdout=None,
            evidence_hash=source['evidence_sha256'], warnings=WARNINGS)
        if body.walk_forward is not None:
            value['walk_forward'] = walk_forward(frozen, body)
            value['warnings'] = [*WARNINGS[:-1], 'Incluye walk-forward con parámetros fijos; faltan sensibilidad y pruebas de sobreajuste.']
        if body.sensitivity is not None:
            value['sensitivity'] = sensitivity(frozen, body, development)
            value['warnings'] = [*value['warnings'][:-1], 'Incluye sensibilidad de un factor cada vez; no es validación estadística ni prueba completa de sobreajuste.']
        signature = digest(snapshot)
        def save(work):
            old = work.get('lab_protocol', ident)
            if old:
                return old
            if digest(self._snapshot(work, body)) != signature:
                raise RevisionConflict('Cambió la evidencia durante el cálculo. Revisa el protocolo de nuevo.')
            self._guard(work, guard)
            work.lab_insert('lab_protocol', value)
            work.lab_insert('lab_summary', summary)
            work.lab_insert('lab_reservation', dict(id=ident, instrument_id=source['instrument_id'],
                start_date=body.holdout_date, end_date=body.end_date))
            work.lab_insert('lab_exposure', dict(id=ident + '-development', instrument_id=source['instrument_id'],
                start_date=body.start_date, end_date=guard['development_end']))
            detail = dict(policy=POLICY, source_hash=source['sha256'])
            for name in ('walk_forward', 'sensitivity'):
                if name in value:
                    detail[name + '_hash'] = value[name]['report_hash']
            work.audit('lab.development_saved', ident, detail)
            return value
        return self._public(self.store.atomic(save))

    @bounded_calculation
    def open_holdout(self, ident, body):
        if body.protocol_hash != ident:
            raise RevisionConflict('La confirmación pertenece a otro protocolo.')
        value = self.store.read(lambda w: self._get(w, ident))
        if value['holdout'] is not None:
            return self._public(value)
        self.store.read(lambda w: self._guard(w, value['protocol'], opening=True))
        result = period(value['frozen'], LabInput.model_validate(value['inputs']), True)
        def save(work):
            current = self._get(work, ident)
            if current['holdout'] is not None:
                return current
            self._guard(work, current['protocol'], opening=True)
            current['holdout'] = result
            current['protocol']['opened'] = True
            summary = current['protocol']
            work.lab_insert('lab_exposure', dict(id=ident + '-holdout', instrument_id=summary['instrument_id'],
                start_date=summary['holdout_date'], end_date=summary['end_date']))
            work.put('lab_protocol', current)
            work.put('lab_summary', summary)
            work.audit('lab.holdout_opened', ident, dict(report_hash=result['report_hash']))
            return current
        return self._public(self.store.atomic(save))

    @bounded_calculation
    def reproduce(self, ident):
        value = self.store.read(lambda w: self._get(w, ident))
        body = LabInput.model_validate(value['inputs'])
        development = period(value['frozen'], body, False)
        holdout = period(value['frozen'], body, True) if value['holdout'] else None
        result = dict(id=ident, development_matches=development == value['development'],
            holdout_matches=holdout == value['holdout'] if holdout else None)
        if 'walk_forward' in value:
            result['walk_forward_matches'] = walk_forward(value['frozen'], body) == value['walk_forward']
        if 'sensitivity' in value:
            result['sensitivity_matches'] = sensitivity(value['frozen'], body, development) == value['sensitivity']
        return result

"""Own price/FX CSV: explicit identity, exact decimals and reviewed versions."""
from datetime import datetime, timezone
import hmac

from .book import BookError, cutoff, number, decimal_text, POLICY
from .catalog import IdentityNotFound, RevisionConflict
from .data import _rows
from .portfolios import fingerprint
from .quality import EvidenceInput, prepare_evidence, timestamp

PRICE_COLUMNS = 'date,listing_ref,open,high,low,close,volume,currency,available_at'.split(',')
FX_COLUMNS = 'date,from_currency,to_currency,rate,available_at'.split(',')


def summary(value):
    evidence = value['quality_evidence'][value['symbol']]
    return {**{k: value[k] for k in ('id', 'kind', 'name', 'source', 'version', 'listing_id', 'symbol', 'currency', 'format_id', 'sha256', 'received_at')},
            'date_min': value['bars'][0]['date'], 'date_max': value['bars'][-1]['date'], 'row_count': len(value['bars']),
            'price_basis': evidence['price_basis'], 'basis_verified': evidence['basis_verified'],
            'calendar_verified': bool(evidence['calendar'] and evidence['calendar']['verified'])}


def parse(kind, body, currency):
    columns = PRICE_COLUMNS if kind == 'prices' else FX_COLUMNS
    values, seen = [], set()
    for line, row in _rows(body.csv, set(columns), set(columns)):
        if len(values) >= 100_000:
            raise BookError('input_limit', 'Máximo 100.000 observaciones por serie.')
        day = cutoff(row['date'])
        if day in seen:
            raise BookError('duplicate_date', 'Fecha duplicada en la serie.', line)
        seen.add(day)
        available = timestamp(row['available_at']).isoformat() if row['available_at'] else None
        if available and timestamp(available).date().isoformat() < day:
            raise BookError('invalid_availability', 'Disponibilidad anterior a la fecha de la observación.', line)
        value = dict(date=day, symbol=body.listing_ref if kind == 'prices' else 'USD_EUR', currency=currency, available_at=available)
        if kind == 'prices':
            if row['listing_ref'] != body.listing_ref or row['currency'] != currency:
                raise BookError('identity_mismatch', 'Referencia o moneda distinta de la cotización elegida.', line)
            numbers = {f: number(row[f], f, 12, line, positive=f != 'volume') for f in ('open', 'high', 'low', 'close', 'volume')}
            if numbers['low'] > min(numbers['open'], numbers['close']) or numbers['high'] < max(numbers['open'], numbers['close']) or numbers['low'] > numbers['high']:
                raise BookError('invalid_ohlc', 'Máximo/mínimo incoherentes con apertura y cierre.', line)
            value.update({k: decimal_text(v) for k, v in numbers.items()})
        else:
            if (row['from_currency'], row['to_currency']) != ('USD', 'EUR'):
                raise BookError('fx_direction', 'La serie debe expresar EUR por USD; no se invierte automáticamente.', line)
            value['rate'] = decimal_text(number(row['rate'], 'rate', 18, line, positive=True))
        values.append(value)
    return sorted(values, key=lambda r: r['date'])


class MarketService:
    def __init__(self, store):
        self.store = store

    def list(self):
        return dict(series=[summary(s) for s in self.store.read(lambda w: w.market_list())])

    def read(self, kind, ident, version, offset=0, limit=100):
        value = self.store.read(lambda w: w.market_version(kind, ident, version))
        if value is None:
            raise IdentityNotFound('Versión de mercado no encontrada.')
        observations = [{k: v for k, v in b.items() if k not in ('symbol', 'currency')} for b in value['bars'][offset:offset+limit]]
        return dict(series=summary(value), evidence=value['quality_evidence'][value['symbol']], observations=observations, offset=offset, limit=limit, total=len(value['bars']))

    def _context(self, work, kind, ident):
        if kind == 'prices' and work.get('dataset', ident) is not None:
            raise ValueError('Ese identificador pertenece a un conjunto anterior; crea una serie nativa independiente.')
        portfolios = work.portfolio_list()
        return dict(current=work.market_current(kind, ident), catalog=work.catalog(), portfolios=portfolios,
                    fx_bindings=[work.portfolio_fx(p['id'], p['revision']) for p in portfolios])

    def import_series(self, kind, body):
        if kind not in ('prices', 'fx'):
            raise ValueError('Tipo de serie desconocido.')
        if kind == 'fx' and body.listing_id is not None:
            raise ValueError('FX no admite una cotización de acciones.')
        ident = body.series_id or fingerprint(['market-series', kind, body.source, body.name, body.listing_id])
        context = self.store.atomic(lambda w: self._context(w, kind, ident))
        current = context['current']
        if body.expected_version != (current['version'] if current else 0):
            raise RevisionConflict('La serie ha cambiado. Actualiza su versión y previsualiza de nuevo.')
        currency, symbol = 'USD', 'USD_EUR'
        if kind == 'prices':
            listing = next((s for s in context['catalog']['listings'] if s['id'] == body.listing_id), None)
            if not listing:
                raise IdentityNotFound('Selecciona una cotización explícita del catálogo.')
            currency, symbol = listing['currency'], body.listing_ref
        bars = parse(kind, body, currency)
        evidence_input = body.evidence or EvidenceInput(symbol=symbol)
        if evidence_input.availability_csv:
            raise ValueError('Este formato lleva available_at en cada fila; no mezcles otra tabla de disponibilidad.')
        evidence = prepare_evidence(evidence_input.model_copy(update={'symbol': symbol}), {'bars': bars})
        evidence['availability'] = {b['date']: b['available_at'] for b in bars}
        evidence['availability_source'] = body.source
        for b in bars:
            calendar_day = (evidence['calendar'] or {}).get('days', {}).get(b['date'])
            if calendar_day and calendar_day['status'] == 'open' and b['available_at'] and timestamp(b['available_at']) < timestamp(calendar_day['close_at']):
                raise ValueError('Una observación de cierre no puede estar disponible antes del cierre acreditado.')
        value = dict(id=ident, kind=kind, name=body.name, source=body.source, listing_id=body.listing_id,
                     symbol=symbol, currency=currency, format_id='atlas-prices-v2' if kind == 'prices' else 'atlas-fx-v1',
                     bars=bars, quality_evidence={symbol: evidence})
        changed, added = 0, len(bars)
        if current:
            if any(value[k] != current[k] for k in ('name', 'source', 'listing_id', 'symbol', 'currency', 'format_id')):
                raise ValueError('La identidad, nombre y fuente de una serie son inmutables; crea otra serie.')
            old, new = ({b['date']: b for b in s['bars']} for s in (current, value))
            if not old.keys() <= new.keys():
                raise ValueError('La revisión completa debe conservar todas las fechas anteriores.')
            changed = sum(old[k] != new[k] for k in old)
            added = len(new.keys() - old.keys())
            backfilled = any(k < max(old) for k in new.keys() - old.keys())
            old_evidence = current['quality_evidence'][symbol]
            evidence_changed = (any(old_evidence.get(k) != evidence.get(k) for k in evidence if k != 'availability') or
                                any(old_evidence.get('availability', {}).get(k) != evidence['availability'].get(k) for k in old))
            if (changed or backfilled or evidence_changed) and (not body.revise_history or len(body.reason.strip()) < 3):
                raise ValueError('Cambiar historia o evidencia requiere revisión explícita y un motivo de al menos tres caracteres.')
        value['sha256'] = fingerprint(value)
        duplicate = bool(current and current['sha256'] == value['sha256'])
        value.update(version=current['version'] if duplicate else (current['version'] + 1 if current else 1),
                     received_at=current['received_at'] if duplicate else datetime.now(timezone.utc).isoformat(),
                     revision_reason=body.reason)
        affected = [p['id'] for p, fx in zip(context['portfolios'], context['fx_bindings']) if
                    (kind == 'prices' and any(b['dataset_id'] == ident for b in p['bindings'])) or
                    (kind == 'fx' and fx and fx['series_id'] == ident)]
        token = fingerprint(dict(purpose='market-import-v1', context=context, body=body.model_dump(exclude={'commit', 'preview_token'})))
        if body.commit:
            if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
                raise RevisionConflict('La previsualización está obsoleta o ausente.')
            def save(work):
                if fingerprint(self._context(work, kind, ident)) != fingerprint(context):
                    raise RevisionConflict('El contexto cambió durante la revisión; no se ha importado.')
                if not duplicate:
                    work.save_market_version(value)
                    work.audit('market.version_imported', ident, dict(kind=kind, version=value['version'], sha256=value['sha256'], reason=body.reason))
            self.store.atomic(save)
        return dict(series=summary(value), added=added, changed=changed, affected_portfolios=affected,
                    committed=body.commit, preview_token=token)

    def fx_binding(self, ident, revision=None):
        def read(work):
            p = work.portfolio_record(ident, revision)
            return {**(work.portfolio_fx(ident, p['revision']) or dict(series_id=None, series_version=None)),
                    'portfolio_id': ident, 'portfolio_revision': p['revision']}
        return self.store.atomic(read)

    def bind_fx(self, ident, body):
        def context(work):
            p = work.portfolio_record(ident)
            return dict(portfolio=p, binding=work.portfolio_fx(ident, p['revision']), series=work.market_version('fx', body.series_id, body.series_version))
        value = self.store.atomic(context)
        if value['portfolio']['accounting_policy'] != POLICY:
            raise ValueError('La cartera heredada conserva su valoración EUR original.')
        if body.expected_revision != value['portfolio']['revision']:
            raise RevisionConflict('La cartera cambió. Vuelve a previsualizar.')
        if value['series'] is None:
            raise IdentityNotFound('Versión FX no encontrada.')
        result = dict(portfolio_id=ident, portfolio_revision=value['portfolio']['revision'], series_id=body.series_id, series_version=body.series_version)
        token = fingerprint(dict(purpose='fx-binding-v1', context=value))
        if body.commit:
            if not body.preview_token or not hmac.compare_digest(token, body.preview_token):
                raise RevisionConflict('Previsualización obsoleta o ausente.')
            def save(work):
                if fingerprint(context(work)) != fingerprint(value):
                    raise RevisionConflict('La cartera cambió durante la confirmación.')
                if value['binding'] and all(value['binding'][k] == result[k] for k in ('series_id', 'series_version')):
                    return result
                saved = work.bind_portfolio_fx(value['portfolio'], value['series'])
                work.audit('portfolio.fx_bound', ident, saved)
                return saved
            result = self.store.atomic(save)
        return dict(**result, committed=body.commit, preview_token=token)

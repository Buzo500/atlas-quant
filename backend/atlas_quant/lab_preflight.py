"""Read-only source inventory, before choosing a simulation or exposing results."""
from typing import Literal
from .contracts import ResponseModel
from .quality import digest, timestamp


class SourceCheck(ResponseModel):
    code: str
    status: Literal['ok', 'block', 'review']
    message: str


class SourcePreflight(ResponseModel):
    series_id: str
    series_version: int
    source_hash: str
    corporate_revision: int
    rows: int
    start: str
    end: str
    checks: list[SourceCheck]
    context_hash: str


def identity_checks(data, listing):
    evidence = data['quality_evidence'][data['symbol']]
    calendar = evidence.get('calendar') or {}
    return [
        dict(code='listing', status='ok' if listing['currency'] == 'EUR' and listing.get('market') else 'block',
             message='Esta simulación requiere una cotización EUR con mercado explícito.'),
        dict(code='basis_calendar', status='ok' if evidence.get('price_basis') == 'raw' and evidence.get('basis_verified') and calendar.get('verified') else 'block',
             message='Importa primero un CSV nativo con base raw y calendario verificados en Datos.'),
        dict(code='market', status='ok' if calendar.get('market') == listing.get('market') else 'block',
             message='El mercado del calendario no coincide con la cotización.'),
    ]


def inspect_source(data, listing, corporate):
    checks = identity_checks(data, listing)
    success = dict(listing='Cotización EUR y mercado explícito.', basis_calendar='Base raw y calendario declarados como verificados.', market='Mercado del calendario y cotización coincidentes.')
    for check in checks:
        if check['status'] == 'ok':
            check['message'] = success[check['code']]
    bars = data['bars']
    dates = sorted(b['date'] for b in bars)
    calendar = data['quality_evidence'][data['symbol']].get('calendar') or {}
    days = calendar.get('days', {})
    expected = {d for d, v in days.items() if dates[0] <= d <= dates[-1] and v['status'] == 'open'}
    missing = len(expected - set(dates))
    outside = len(set(dates) - expected)
    unavailable = sum(not b.get('available_at') for b in bars)
    early = sum(bool(b.get('available_at') and days.get(b['date'], {}).get('close_at') and
                     timestamp(b['available_at']) < timestamp(days[b['date']]['close_at'])) for b in bars)
    events = sum(e['listing_id'] == listing['id'] and not e['cancelled'] and
        (not any(e.get(k) for k in ('effective_date', 'ex_date', 'payment_date')) or
         any(dates[0] <= e[k] <= dates[-1] for k in ('effective_date', 'ex_date', 'payment_date') if e.get(k)))
        for e in corporate['events'])
    checks.extend([
        dict(code='coverage', status='review' if missing or outside or not calendar.get('verified') else 'ok',
             message=f'{missing} sesiones sin barra y {outside} barras fuera de sesiones abiertas en el calendario declarado.' + (' Un calendario sin acreditar no permite concluir cobertura.' if not calendar.get('verified') else '')),
        dict(code='availability', status='review' if unavailable or early else 'ok',
             message=f'{unavailable} cierres sin disponibilidad y {early} anteriores al cierre declarado.' + (' El periodo elegido debe excluir o resolver esas filas.' if unavailable or early else '')),
        dict(code='events', status='review', message=f'{events} eventos conocidos afectan al rango o carecen de fecha. Su ausencia en ATLAS no acredita un periodo libre de eventos.'),
        dict(code='protocol', status='review', message='Pendiente al configurar: aperturas y su disponibilidad, cierre antes de la siguiente apertura, periodo libre de eventos, calentamiento, límites y reserva temporal.'),
    ])
    result = dict(series_id=data['id'], series_version=data['version'], source_hash=data['sha256'],
        corporate_revision=corporate['revision'], rows=len(bars), start=dates[0], end=dates[-1], checks=checks)
    return dict(**result, context_hash=digest(result))

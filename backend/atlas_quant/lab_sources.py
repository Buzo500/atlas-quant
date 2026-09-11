"""CSV/native data boundary. Assertions stay attributed, never inferred."""
from datetime import datetime, timezone
from .data import _rows
from .quality import digest, timestamp
from .strategy_spec import FrozenCalendar, FrozenPriceSource, TradingSession


def freeze_source(data, listing, corporate, body):
    if not body.evidence_reviewed:
        raise ValueError('Revisa y confirma la procedencia de aperturas y ausencia de eventos.')
    if not body.start_date < body.holdout_date <= body.end_date < datetime.now(timezone.utc).date().isoformat():
        raise ValueError('Orden requerido: inicio < prueba final <= fin, todos anteriores a hoy.')
    if listing['currency'] != 'EUR' or not listing.get('market'):
        raise ValueError('Esta simulación requiere una cotización EUR con mercado explícito.')
    evidence = data['quality_evidence'][data['symbol']]
    calendar = evidence.get('calendar') or {}
    if evidence.get('price_basis') != 'raw' or not evidence.get('basis_verified') or not calendar.get('verified'):
        raise ValueError('Importa primero un CSV nativo con base raw y calendario verificados en Datos.')
    if calendar['market'] != listing['market']:
        raise ValueError('El mercado del calendario no coincide con la cotización.')
    if calendar['start'] > body.start_date or calendar['end'] < body.end_date:
        raise ValueError('El calendario acreditado no cubre el periodo solicitado.')
    expected = {d: r for d, r in calendar['days'].items()
                if body.start_date <= d <= body.end_date and r['status'] == 'open'}
    if len(expected) > 2000:
        raise ValueError('Máximo 2.000 sesiones por protocolo.')
    columns = {'date', 'open_at', 'close_at', 'open_available_at'}
    sessions, availability = [], {}
    for _, row in _rows(body.sessions_csv, columns, columns):
        if len(sessions) >= 2000:
            raise ValueError('Máximo 2.000 sesiones por protocolo.')
        session = TradingSession(**{k: row[k] for k in ('date', 'open_at', 'close_at')})
        if session.date not in expected or session.date in availability:
            raise ValueError('Aperturas duplicadas o fuera de las sesiones acreditadas del periodo.')
        if timestamp(expected[session.date]['close_at']) != timestamp(session.close_at):
            raise ValueError('El cierre difiere del calendario acreditado.')
        available = timestamp(row['open_available_at']).isoformat() if row['open_available_at'] else None
        if available and timestamp(available) < timestamp(session.open_at):
            raise ValueError('El precio de apertura no puede conocerse antes de la apertura.')
        sessions.append(session)
        availability[session.date] = available
    if set(availability) != set(expected):
        raise ValueError('Declara todas las sesiones abiertas del periodo, sin omitir huecos.')
    frozen = FrozenCalendar(id=digest(calendar), version=data['version'], source=body.opening_source,
        market=listing['market'], timezone=calendar['timezone'], verified=True, sessions=tuple(sessions))
    if body.holdout_date not in expected:
        raise ValueError('La prueba final debe comenzar en una sesión abierta.')
    lengths = [sum(s.date < body.holdout_date for s in sessions), sum(s.date >= body.holdout_date for s in sessions)]
    if min(lengths) < body.slow + 2:
        raise ValueError('Cada periodo necesita al menos ventana lenta + 2 sesiones; el calentamiento es independiente.')
    for event in corporate['events']:
        if event['listing_id'] != listing['id'] or event['cancelled']:
            continue
        dates = [event.get(k) for k in ('effective_date', 'ex_date', 'payment_date') if event.get(k)]
        if not dates or any(body.start_date <= d <= body.end_date for d in dates):
            raise ValueError('Hay eventos corporativos conocidos incompatibles con la declaración de periodo libre de eventos.')
    bars = {b['date']: b for b in data['bars'] if body.start_date <= b['date'] <= body.end_date}
    if set(bars) - set(expected):
        raise ValueError('Existen barras fuera del calendario de sesiones abiertas.')
    next_opens = {a.date: b.open_at for a, b in zip(sessions, sessions[1:])}
    for day, bar in bars.items():
        if not bar['available_at'] or timestamp(bar['available_at']) < timestamp(expected[day]['close_at']):
            raise ValueError('Cada cierre debe tener disponibilidad acreditada, posterior o igual al cierre.')
        deadline = timestamp(next_opens[day]) if day in next_opens else datetime.now(timezone.utc)
        if timestamp(bar['available_at']) >= deadline:
            raise ValueError('Este protocolo requiere cierres disponibles antes de la siguiente apertura y no futuros.')
    assertions = dict(evidence=evidence, openings=body.sessions_csv, opening_source=body.opening_source,
                      event_free_source=body.event_free_source, reviewed=True, corporate_revision=corporate['revision'])
    source = FrozenPriceSource(kind='native', id=data['id'], version=data['version'], sha256=data['sha256'],
        instrument_id=listing['instrument_id'], listing_id=listing['id'], market=listing['market'],
        basis_verified=True, evidence_sha256=digest(assertions))
    return dict(source=source.model_dump(mode='json'), calendar=frozen.model_dump(mode='json'),
                bars=bars, openings=availability, assertions=assertions)

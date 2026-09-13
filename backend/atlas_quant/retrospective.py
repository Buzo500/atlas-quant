"""Explicit retrospective assumptions, isolated from accredited laboratory inputs.

No persistence or network. Only development reaches the shared economic replay.
False evidence flags remain false in specifications, reports and exports.
"""
import csv
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from functools import cached_property
import hashlib
import io
import json
import re
from types import SimpleNamespace
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator

from .lab_economics import window_period
from .quality import digest
from .simulation_contracts import SimulationConfig
from .strategy_spec import (
    EVALUATOR_VERSION, FrozenCalendar, FrozenContract, Hash, Identifier, SmaSpec, TradingSession,
)

POLICY = 'atlas-retrospective-eur-v1'
MAX_BYTES = 2_000_000
CSV_FIELDS = ('date', 'open', 'high', 'low', 'close', 'volume', 'dividends', 'splits')
WARNINGS = (
    'Investigación retrospectiva: precios observados, disponibilidad y ejecución supuestas.',
    'Base raw solicitada al proveedor; no se acredita su historial de correcciones.',
    'Ausencia de eventos limitada al contraste declarado; no es certificación exhaustiva.',
    'Apertura OHLC como fill hipotético, con costes; sin liquidez, cola ni ejecución garantizada.',
    'Reserva excluida del cálculo, sin acreditar exposición externa ni registrar reservas globales.',
    'Un activo elegido retrospectivamente no representa un universo libre de sesgo de selección.',
    'No acredita una estrategia ni autoriza paper, órdenes o cambios en carteras.',
)


class RetrospectiveSource(FrozenContract):
    kind: Literal['retrospective'] = 'retrospective'
    id: Identifier
    version: int = Field(ge=1)
    sha256: Hash
    instrument_id: Identifier
    listing_id: Identifier
    market: Identifier
    currency: Literal['EUR'] = 'EUR'
    price_basis: Literal['raw'] = 'raw'
    basis_verified: Literal[False] = False
    evidence_sha256: Hash
    corporate_policy: Literal['assumed-event-free-v1'] = 'assumed-event-free-v1'

    @field_validator('basis_verified', mode='before')
    @classmethod
    def exact_boolean(cls, value):
        if value is not False:
            raise ValueError('La fuente retrospectiva no acredita base verificada.')
        return value


class RetrospectiveCalendar(FrozenContract):
    id: Identifier
    version: int = Field(ge=1)
    source: str = Field(min_length=3, max_length=500)
    market: Identifier
    timezone: str
    verified: Literal[False] = False
    sessions: tuple[TradingSession, ...] = Field(min_length=2, max_length=2000)

    @field_validator('verified', mode='before')
    @classmethod
    def exact_boolean(cls, value):
        if value is not False:
            raise ValueError('Los horarios modelados no son evidencia verificada.')
        return value

    @model_validator(mode='after')
    def ordered(self):
        return FrozenCalendar.ordered(self)


class RetrospectiveSpec(FrozenContract):
    schema_version: Literal[1] = 1
    strategy: Literal['sma-cross-long-v1'] = 'sma-cross-long-v1'
    strategy_id: Identifier
    revision: int = Field(ge=1)
    fast: int = Field(default=20, ge=2, le=249)
    slow: int = Field(default=50, ge=3, le=250)
    research_policy: Literal['atlas-retrospective-eur-v1'] = POLICY
    source: RetrospectiveSource
    calendar: RetrospectiveCalendar
    missing_policy: Literal['reset-warmup-preserve-target-v1'] = 'reset-warmup-preserve-target-v1'
    execution_policy: Literal['strict-next-open-v1'] = 'strict-next-open-v1'
    target_basis: Literal['strategy-budget'] = 'strategy-budget'

    @model_validator(mode='after')
    def windows(self):
        return SmaSpec.windows(self)

    @cached_property
    def fingerprint(self):
        return digest({'evaluator': EVALUATOR_VERSION, 'spec': self.model_dump(mode='json')})


class RetrospectiveRequest(FrozenContract):
    policy: Literal['atlas-retrospective-eur-v1'] = POLICY
    symbol: Identifier
    instrument_id: Identifier
    market: Identifier
    currency: Literal['EUR'] = 'EUR'
    timezone: Literal['Europe/Berlin'] = 'Europe/Berlin'
    expected_dates: tuple[str, ...] = Field(min_length=2, max_length=2000)
    early_close_dates: tuple[str, ...] = ()
    holdout_date: str
    fast: int = Field(default=20, ge=2, le=249)
    slow: int = Field(default=50, ge=3, le=250)
    config: SimulationConfig
    provider: str = Field(min_length=3, max_length=500)
    calendar_source: str = Field(min_length=3, max_length=3000)
    event_review: str = Field(min_length=10, max_length=3000)
    source_sha256: Hash
    acknowledge_assumptions: Literal[True]

    @field_validator('acknowledge_assumptions', mode='before')
    @classmethod
    def acknowledged(cls, value):
        if value is not True:
            raise ValueError('Acepta expresamente los supuestos retrospectivos.')
        return value

    @model_validator(mode='after')
    def coherent(self):
        dates = self.expected_dates
        if list(dates) != sorted(set(dates)) or any(date.fromisoformat(d).isoformat() != d for d in dates):
            raise ValueError('Calendario ISO completo, ordenado y sin duplicados requerido.')
        if self.fast >= self.slow or self.holdout_date not in dates:
            raise ValueError('Ventanas o corte de reserva inválidos.')
        if len(set(self.early_close_dates)) != len(self.early_close_dates) or set(self.early_close_dates)-set(dates):
            raise ValueError('Cierres abreviados fuera del calendario o duplicados.')
        split = dates.index(self.holdout_date)
        if min(split, len(dates)-split) < self.slow+2:
            raise ValueError('Desarrollo y reserva necesitan ventana lenta + 2 sesiones.')
        return self

    @cached_property
    def fingerprint(self):
        return digest(self.model_dump(mode='json'))


def parse_prices(document, request):
    if len(document.encode('utf-8')) > MAX_BYTES:
        raise ValueError('CSV demasiado grande.')
    if hashlib.sha256(document.encode('utf-8')).hexdigest() != request.source_sha256:
        raise ValueError('La huella del CSV no coincide con el protocolo.')
    return validate_prices(document, request.expected_dates)


def validate_prices(document, expected_dates):
    if len(document.encode('utf-8')) > MAX_BYTES:
        raise ValueError('CSV demasiado grande.')
    reader = csv.DictReader(io.StringIO(document))
    if reader.fieldnames != list(CSV_FIELDS):
        raise ValueError('Columnas CSV retrospectivas incorrectas.')
    rows = []
    try:
        for row in reader:
            if len(rows) >= 2000 or None in row or any(v is None for v in row.values()):
                raise ValueError('Fila incompleta o límite de sesiones excedido.')
            prices = [Decimal(row[k]) for k in ('open', 'high', 'low', 'close')]
            if any(not p.is_finite() or p <= 0 or p >= 10**12 or p.as_tuple().exponent < -12 for p in prices):
                raise ValueError('Precios positivos, finitos y con hasta 12 decimales requeridos.')
            op, hi, lo, cl = prices
            if not lo <= min(op, cl) <= max(op, cl) <= hi:
                raise ValueError('OHLC incoherente.')
            if not row['volume'].isdigit() or not 0 < int(row['volume']) <= 10**15:
                raise ValueError('Volumen entero positivo requerido para la referencia de apertura.')
            if Decimal(row['dividends']) != 0 or Decimal(row['splits']) != 0:
                raise ValueError('Evento corporativo conocido: este modo no lo modela.')
            for key in ('open', 'high', 'low', 'close'):
                row[key] = format(Decimal(row[key]), 'f')
            rows.append(row)
    except (InvalidOperation, csv.Error) as exc:
        raise ValueError('CSV inválido.') from exc
    if [r['date'] for r in rows] != list(expected_dates):
        raise ValueError('Las filas no coinciden exactamente con el calendario declarado.')
    return rows


def freeze(request, document):
    rows = parse_prices(document, request)
    # This public frozen artifact never contains holdout prices.
    development = [r for r in rows if r['date'] < request.holdout_date]
    reserved = [r for r in rows if r['date'] >= request.holdout_date]
    holdout = dict(start=request.holdout_date, end=reserved[-1]['date'], sessions=len(reserved),
                   rows_hash=digest(reserved), evaluated=False, external_exposure='unverified')
    return freeze_development(request, development, holdout)


def prices_csv(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def freeze_development(request, development, holdout):
    zone = ZoneInfo(request.timezone)
    def instant(day, hour, minute=0):
        return datetime.combine(date.fromisoformat(day), time(hour, minute), zone).isoformat()
    sessions = [dict(date=r['date'], open_at=instant(r['date'], 9),
                     close_at=instant(r['date'], 14 if r['date'] in request.early_close_dates else 17,
                                      0 if r['date'] in request.early_close_dates else 30)) for r in development]
    source = RetrospectiveSource(id=request.symbol, version=1, sha256=request.source_sha256,
        instrument_id=request.instrument_id, listing_id=request.symbol, market=request.market,
        evidence_sha256=request.fingerprint)
    calendar = RetrospectiveCalendar(id=request.fingerprint, version=1,
        source='Horarios modelados por atlas-retrospective-eur-v1', market=request.market,
        timezone=request.timezone, sessions=tuple(sessions))
    spec = RetrospectiveSpec(strategy_id='lab-sma', revision=1, fast=request.fast, slow=request.slow,
                             source=source, calendar=calendar)
    payload = dict(policy=POLICY, request=request.model_dump(mode='json'), spec=spec.model_dump(mode='json'),
        rows=development, close_availability={r['date']: instant(r['date'], 18) for r in development},
        holdout=holdout,
        warnings=list(WARNINGS))
    return dict(**payload, frozen_hash=digest(payload))


def evaluate(frozen):
    if not isinstance(frozen, dict) or frozen.get('policy') != POLICY or digest({k:v for k,v in frozen.items() if k != 'frozen_hash'}) != frozen.get('frozen_hash'):
        raise ValueError('Protocolo retrospectivo alterado o desconocido.')
    request = RetrospectiveRequest.model_validate_json(json.dumps(frozen['request']))
    spec = RetrospectiveSpec.model_validate_json(json.dumps(frozen['spec']))
    dates = [d for d in request.expected_dates if d < request.holdout_date]
    if [r['date'] for r in frozen['rows']] != dates or [s.date for s in spec.calendar.sessions] != dates:
        raise ValueError('El desarrollo contiene fechas incompletas o reservadas.')
    if spec.fast != request.fast or spec.slow != request.slow or spec.source.evidence_sha256 != request.fingerprint:
        raise ValueError('Especificación distinta del protocolo.')
    rows = validate_prices(prices_csv(frozen['rows']), dates)
    reserved = [d for d in request.expected_dates if d >= request.holdout_date]
    holdout = frozen['holdout']
    if (not isinstance(holdout, dict)
        or set(holdout) != {'start', 'end', 'sessions', 'rows_hash', 'evaluated', 'external_exposure'}
        or holdout.get('evaluated') is not False or holdout.get('external_exposure') != 'unverified'
        or holdout.get('start') != reserved[0] or holdout.get('end') != reserved[-1]
        or type(holdout.get('sessions')) is not int or holdout['sessions'] != len(reserved)
        or not isinstance(holdout.get('rows_hash'), str) or not re.fullmatch('[0-9a-f]{64}', holdout['rows_hash'])):
        raise ValueError('Resumen de reserva inválido.')
    if freeze_development(request, rows, holdout) != frozen:
        raise ValueError('Los supuestos o el contenido difieren del protocolo canónico.')
    data = dict(source=spec.source.model_dump(mode='json'), calendar=spec.calendar.model_dump(mode='json'),
        bars={r['date']:dict(r, available_at=frozen['close_availability'][r['date']]) for r in frozen['rows']},
        openings={s.date:s.open_at for s in spec.calendar.sessions})
    body = SimpleNamespace(fast=request.fast, slow=request.slow, config=request.config)
    result = window_period(data, body, 0, len(dates), spec_type=RetrospectiveSpec)
    return dict(policy=POLICY, frozen_hash=frozen['frozen_hash'], development=result,
                holdout=frozen['holdout'], warnings=list(WARNINGS), evidence_verified=False)

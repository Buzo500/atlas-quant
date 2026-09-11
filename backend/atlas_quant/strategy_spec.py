"""Restricted v0.6 research contracts. No executable expressions or I/O.

Verified evidence is an input assertion from the data boundary, not something
this pure module can certify. Frozen source hashes must be checked there.
"""
from __future__ import annotations

from datetime import date
from functools import cached_property
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .quality import digest, timestamp

EVALUATOR_VERSION = 'sma-cross-evaluator-v1'
Hash = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_.:/-]+$')]
Price = Annotated[str, Field(pattern=r'^(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,12})?$')]


class FrozenContract(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)


def utc(value: str) -> str:
    return timestamp(value).isoformat()


def price_units(value: str) -> int:
    """Exact fixed-point arithmetic, independent of the ambient Decimal context."""
    whole, _, fraction = value.partition('.')
    return int(whole) * 10**12 + int(fraction.ljust(12, '0'))


def normalized_price(value: str) -> str:
    if price_units(value) <= 0:
        raise ValueError('El precio debe ser positivo.')
    return value.rstrip('0').rstrip('.') if '.' in value else value


class FrozenPriceSource(FrozenContract):
    kind: Literal['synthetic', 'native', 'legacy']
    id: Identifier
    version: int = Field(ge=1)
    sha256: Hash
    instrument_id: Identifier
    listing_id: Identifier
    market: Identifier
    currency: Literal['EUR'] = 'EUR'
    price_basis: Literal['raw'] = 'raw'
    basis_verified: Literal[True]
    evidence_sha256: Hash
    corporate_policy: Literal['verified-event-free-v1'] = 'verified-event-free-v1'

    @field_validator('basis_verified', mode='before')
    @classmethod
    def exact_boolean(cls, value):
        if value is not True:
            raise ValueError('Se requiere evidencia explícita y verificada.')
        return value


class TradingSession(FrozenContract):
    date: str
    open_at: str
    close_at: str

    @field_validator('date')
    @classmethod
    def valid_date(cls, value):
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('Fecha de sesión ISO requerida.')
        return value

    @field_validator('open_at', 'close_at')
    @classmethod
    def valid_time(cls, value):
        return utc(value)

    @model_validator(mode='after')
    def ordered(self):
        if timestamp(self.open_at) >= timestamp(self.close_at):
            raise ValueError('La apertura debe ser anterior al cierre.')
        return self


class FrozenCalendar(FrozenContract):
    id: Identifier
    version: int = Field(ge=1)
    source: str = Field(min_length=3, max_length=500)
    market: Identifier
    timezone: str = Field(min_length=1, max_length=100)
    verified: Literal[True]
    sessions: tuple[TradingSession, ...] = Field(min_length=2, max_length=20_000)

    @field_validator('verified', mode='before')
    @classmethod
    def exact_boolean(cls, value):
        if value is not True:
            raise ValueError('El calendario requiere evidencia verificada.')
        return value

    @model_validator(mode='after')
    def ordered(self):
        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError('Zona IANA desconocida.') from exc
        for session in self.sessions:
            if any(timestamp(value).astimezone(zone).date().isoformat() != session.date
                   for value in (session.open_at, session.close_at)):
                raise ValueError('La sesión diaria debe coincidir con su fecha local.')
        for prior, current in zip(self.sessions, self.sessions[1:]):
            if prior.date >= current.date or timestamp(prior.close_at) >= timestamp(current.open_at):
                raise ValueError('Calendario duplicado, desordenado o con sesiones solapadas.')
        return self


class SmaSpec(FrozenContract):
    schema_version: Literal[1] = 1
    strategy: Literal['sma-cross-long-v1'] = 'sma-cross-long-v1'
    strategy_id: Identifier
    revision: int = Field(ge=1)
    fast: int = Field(default=20, ge=2, le=249)
    slow: int = Field(default=50, ge=3, le=250)
    source: FrozenPriceSource
    calendar: FrozenCalendar
    missing_policy: Literal['reset-warmup-preserve-target-v1'] = 'reset-warmup-preserve-target-v1'
    execution_policy: Literal['strict-next-open-v1'] = 'strict-next-open-v1'
    target_basis: Literal['strategy-budget'] = 'strategy-budget'

    @model_validator(mode='after')
    def windows(self):
        if self.fast >= self.slow:
            raise ValueError('La ventana rápida debe ser menor que la lenta.')
        if self.calendar.market != self.source.market:
            raise ValueError('El calendario y la cotización pertenecen a mercados distintos.')
        return self

    @cached_property
    def fingerprint(self) -> str:
        return digest({'evaluator': EVALUATOR_VERSION, 'spec': self.model_dump(mode='json')})


class CloseObservation(FrozenContract):
    spec_hash: Hash
    session_index: int = Field(ge=0)
    status: Literal['observed', 'missing', 'unverified', 'corporate_action'] = 'observed'
    close: Price | None = None
    available_at: str | None = None
    decision_at: str

    @field_validator('close')
    @classmethod
    def valid_price(cls, value):
        return normalized_price(value) if value is not None else None

    @field_validator('available_at', 'decision_at')
    @classmethod
    def valid_time(cls, value):
        return utc(value) if value is not None else None

    @model_validator(mode='after')
    def observed_fields(self):
        if self.status == 'observed' and (self.close is None or self.available_at is None):
            raise ValueError('Un cierre observado necesita precio y disponibilidad acreditada.')
        if self.status != 'observed' and (self.close is not None or self.available_at is not None):
            raise ValueError('Un dato bloqueado no debe incluir un precio utilizable.')
        return self


class StrategyState(FrozenContract):
    schema_version: Literal[1] = 1
    evaluator: Literal['sma-cross-evaluator-v1'] = EVALUATOR_VERSION
    spec_hash: Hash
    last_index: int = Field(default=-1, ge=-1)
    last_observation_hash: Hash | None = None
    last_decision_at: str | None = None
    prefix_hash: Hash
    closes: tuple[Price, ...] = Field(default=(), max_length=250)
    target_weight: Literal[0, 1] = 0
    halted_reason: Literal['corporate_action'] | None = None

    @field_validator('target_weight', 'schema_version', mode='before')
    @classmethod
    def exact_integer(cls, value):
        if type(value) is not int:
            raise ValueError('Entero estricto requerido.')
        return value

    @field_validator('closes')
    @classmethod
    def valid_prices(cls, values):
        return tuple(normalized_price(value) for value in values)

    @field_validator('last_decision_at')
    @classmethod
    def valid_time(cls, value):
        return utc(value) if value is not None else None

    @model_validator(mode='after')
    def consistent_cursor(self):
        if self.last_index == -1:
            if self.last_observation_hash is not None or self.last_decision_at is not None or self.closes or self.target_weight or self.halted_reason:
                raise ValueError('Estado inicial incoherente.')
        elif self.last_observation_hash is None or self.last_decision_at is None or len(self.closes) > self.last_index + 1:
            raise ValueError('Cursor de estrategia incompleto.')
        if self.halted_reason and self.closes:
            raise ValueError('Un evento corporativo sin resolver no conserva calentamiento utilizable.')
        return self


class TargetIntent(FrozenContract):
    key: Hash
    spec_hash: Hash
    strategy_id: Identifier
    instrument_id: Identifier
    listing_id: Identifier
    session_index: int = Field(ge=0)
    session_date: str
    decision_at: str
    target_weight: Literal[0, 1]
    target_basis: Literal['strategy-budget'] = 'strategy-budget'
    reason: Literal['cross_up', 'cross_down']
    next_open_at: str | None
    status: Literal['pending', 'expired']
    expiry_reason: Literal['decision_not_before_next_open', 'next_session_unknown'] | None = None


class EvaluationResult(FrozenContract):
    state: StrategyState
    status: Literal['warming', 'evaluated', 'blocked', 'waiting', 'duplicate']
    reasons: tuple[str, ...] = ()
    intent: TargetIntent | None = None


class OpeningObservation(FrozenContract):
    spec_hash: Hash
    open_at: str
    decision_at: str
    price: Price | None = None
    available_at: str | None = None

    @field_validator('price')
    @classmethod
    def valid_price(cls, value):
        return normalized_price(value) if value is not None else None

    @field_validator('open_at', 'decision_at', 'available_at')
    @classmethod
    def valid_time(cls, value):
        return utc(value) if value is not None else None

    @model_validator(mode='after')
    def coherent_quote(self):
        if (self.price is None) != (self.available_at is None):
            raise ValueError('La apertura necesita precio y disponibilidad juntos.')
        if self.available_at and timestamp(self.available_at) < timestamp(self.open_at):
            raise ValueError('No puede conocerse el precio de apertura antes de la apertura.')
        return self

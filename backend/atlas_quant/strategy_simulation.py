"""Offline SMA economics. One coordinator, the existing native book authority.

No store, network, global clock, broker or legacy backtest integration. Recovery
replays the bounded input journal instead of trusting an editable cash snapshot.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal as D, localcontext, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN
import json
from zoneinfo import ZoneInfo

from .book import CENT, SCALE, NativeBook, decimal_text as text
from .quality import digest, timestamp
from .simulation_contracts import SimulationConfig, SIMULATOR_VERSION
from .strategy_evaluator import evaluate, initial_state, opening_eligibility
from .strategy_spec import CloseObservation, OpeningObservation, SmaSpec

ZERO = D(0)
MAX_EVENTS = 40_000
MAX_CHECKPOINT_BYTES = 32_000_000


def _entry(day, sequence, kind, gross, fee=ZERO, *, listing=None, quantity=None, price=None, key=None):
    event = dict(external_id=key or 'simulation-capital', date=day, day_sequence=sequence,
                 kind=kind, listing_id=listing, currency='EUR', gross_amount=text(gross, money=True),
                 fee_amount=text(fee, money=True), tax_amount='0.00',
                 quantity=text(quantity) if quantity is not None else None,
                 unit_price=text(price) if price is not None else None)
    return dict(date=day, day_sequence=sequence, listing_id=listing, event=event)


def _account(book, day, listing):
    snapshot = book.snapshot(day)
    cash = D(snapshot['balances'][0]['cash'])
    quantity = next((D(p['quantity']) for p in snapshot['positions'] if p['listing_id'] == listing), ZERO)
    return snapshot, cash, quantity


def _valuation(book, day, listing, mark, config):
    snapshot, cash, quantity = _account(book, day, listing)
    if mark is None and quantity:
        return dict(book=snapshot, nav_eur=None, position_weight=None, risk='valuation_unavailable')
    position = quantity * (mark or ZERO)
    nav = cash + position
    weight = position / nav if nav else ZERO
    return dict(book=snapshot, nav_eur=text(nav), position_weight=text(weight),
                risk='position_limit_exceeded' if position > D(config.max_position_weight)*nav else 'within_limit')


def _execute(book, spec, config, intent, opening, day):
    """Stage a fill on a separate NativeBook; a rejection leaves the input intact."""
    _, cash, held = _account(book, day, spec.source.listing_id)
    side = 'buy' if intent.target_weight else 'sell'
    result = dict(intent_key=intent.key, side=side, status='rejected', reason=None, fill=None)
    if side == 'buy' and not config.purchases_enabled:
        return book, {**result, 'reason': 'purchases_disabled'}, None
    if side == 'buy' and D(config.strategy_weight) > D(config.max_position_weight):
        return book, {**result, 'reason': 'target_exceeds_position_limit'}, None
    if (side == 'buy' and held) or (side == 'sell' and not held):
        return book, {**result, 'status': 'no_trade', 'reason': 'position_already_satisfies_intent'}, None
    mark = D(opening.price)
    slip = D(config.slippage_bps)/10000
    price = (mark * (1 + slip if side == 'buy' else 1 - slip)).quantize(
        SCALE, rounding=ROUND_CEILING if side == 'buy' else ROUND_FLOOR)
    if price <= 0:
        return book, {**result, 'reason': 'fill_price_below_precision'}, None

    def economics(quantity):
        gross = (quantity * price).quantize(CENT, rounding=ROUND_HALF_EVEN)
        fee = (D(config.fixed_fee_eur) + gross*D(config.fee_bps)/10000).quantize(CENT, rounding=ROUND_CEILING)
        return gross, fee

    if side == 'buy':
        step = D(config.quantity_step)
        # Upper bound ignores fees; the predicate includes actual cent rounding
        # and exposure AFTER both fees and adverse execution at the raw mark.
        low, high = 0, int(min((cash+CENT/2)/(step*price), D(10**12)/step))
        while low < high:
            mid = (low + high + 1)//2
            quantity = step*mid
            gross, fee = economics(quantity)
            remaining = cash-gross-fee
            position = quantity*mark
            if remaining >= 0 and position <= D(config.strategy_weight)*(remaining+position):
                low = mid
            else:
                high = mid-1
        quantity = step*low
    else:
        quantity = held
    gross, fee = economics(quantity)
    if not quantity or gross <= 0:
        return book, {**result, 'reason': 'insufficient_budget_for_lot'}, None
    if side == 'sell' and cash+gross-fee < 0:
        return book, {**result, 'reason': 'insufficient_cash_for_sale_fee'}, None
    entry = _entry(day, 1, side, gross, fee, listing=spec.source.listing_id,
                   quantity=quantity, price=price, key=intent.key)
    candidate = deepcopy(book)
    candidate.apply(entry)
    # Book is the economic authority; independently check its staged result.
    _, after_cash, after_quantity = _account(candidate, day, spec.source.listing_id)
    if after_cash < 0 or after_quantity < 0:
        raise ValueError('El libro simulado incumple efectivo o posición no negativos.')
    position = after_quantity*mark
    if side == 'buy' and position > D(config.max_position_weight)*(after_cash+position):
        return book, {**result, 'reason': 'position_limit_exceeded'}, None
    fill = dict(date=day, open_at=opening.open_at, quantity=text(quantity),
                reference_price_eur=text(mark), price_eur=text(price), gross_eur=text(gross, money=True),
                fee_eur=text(fee, money=True), slippage_eur=text(quantity*abs(price-mark)),
                settlement_adjustment_eur=text((gross-quantity*price)*(1 if side == 'buy' else -1)))
    return candidate, {**result, 'status': 'filled', 'fill': fill}, entry


class SmaSimulation:
    """Incremental research coordinator; process commits each valid event atomically in memory."""
    def __init__(self, spec: SmaSpec, config: SimulationConfig):
        self.spec, self.config = spec, config
        self.context_hash = digest(dict(simulator=SIMULATOR_VERSION, spec=spec.fingerprint, config=config.fingerprint))
        self._strategy = initial_state(spec)
        self._pending = None
        self._book = NativeBook()
        self._day = spec.calendar.sessions[0].date
        initial = _entry(self._day, 0, 'deposit', D(config.initial_cash_eur))
        self._book.apply(initial)
        self._journal = [initial]
        self._events, self._records = [], []
        self._last_at, self._last_hash = None, None
        self._last_open_index, self._last_open_hash = -1, None
        self._opens = {s.open_at: i for i, s in enumerate(spec.calendar.sessions)}
        self._mark = None
        self._mark_at = None

    def process(self, event: CloseObservation | OpeningObservation):
        with localcontext() as context:
            context.prec, context.rounding = 64, ROUND_HALF_EVEN
            return self._process(event)

    def _process(self, event):
        if not isinstance(event, (CloseObservation, OpeningObservation)):
            raise ValueError('Se requiere una observación de cierre o apertura validada.')
        if event.spec_hash != self.spec.fingerprint:
            raise ValueError('La observación pertenece a otra especificación.')
        kind = 'close' if isinstance(event, CloseObservation) else 'open'
        payload = dict(kind=kind, observation=event.model_dump(mode='json'))
        event_hash = digest(payload)
        if event_hash == self._last_hash:
            return dict(status='duplicate', event_hash=event_hash)
        if len(self._events) >= MAX_EVENTS:
            raise ValueError('Máximo 40.000 eventos por simulación.')
        now = timestamp(event.decision_at)
        if self._last_at and now < timestamp(self._last_at):
            raise ValueError('El reloj económico no puede retroceder.')
        if now < timestamp(self.spec.calendar.sessions[0].open_at):
            return dict(status='waiting', reason='simulation_not_started', event_hash=event_hash)
        strategy, pending, book, mark = self._strategy, self._pending, self._book, self._mark
        mark_at = self._mark_at
        # A late observation belongs to its old market session, but balances
        # contain all events already consumed at the current economic clock.
        day = now.astimezone(ZoneInfo(self.spec.calendar.timezone)).date().isoformat()
        executions, entry, evaluation = [], None, None
        open_index, open_hash = self._last_open_index, self._last_open_hash
        if kind == 'open':
            if event.open_at not in self._opens:
                raise ValueError('La apertura no figura en el calendario congelado.')
            index = self._opens[event.open_at]
            content_hash = digest(event.model_dump(mode='json', exclude={'decision_at'}))
            if index < open_index or (index == open_index and content_hash != open_hash):
                raise ValueError('Apertura consumida o corregida: requiere otro replay.')
            if index == open_index:
                return dict(status='duplicate', event_hash=event_hash)
            if now < timestamp(event.open_at):
                return dict(status='waiting', reason='waiting_for_open', event_hash=event_hash)
            open_index, open_hash = index, content_hash
        else:
            evaluation = evaluate(self.spec, strategy, event)
            strategy = evaluation.state

        if pending and now > timestamp(pending.next_open_at):
            executions.append(dict(intent_key=pending.key, status='expired',
                                   reason='opening_opportunity_expired', fill=None))
            pending = None
        if kind == 'open':
            if pending:
                if timestamp(event.open_at) < timestamp(pending.next_open_at):
                    raise ValueError('Apertura anterior a la oportunidad pendiente.')
                eligible = opening_eligibility(pending, event)
                if eligible == 'eligible':
                    book, outcome, entry = _execute(book, self.spec, self.config, pending, event, day)
                    executions.append(outcome)
                else:
                    executions.append(dict(intent_key=pending.key, status='expired', reason=eligible, fill=None))
                pending = None
            quote_at = event.open_at
            quote = (D(event.price) if event.price and timestamp(event.available_at) <= now
                     and not strategy.halted_reason else None)
        elif evaluation.status not in ('waiting', 'duplicate'):
            quote_at = self.spec.calendar.sessions[event.session_index].close_at
            quote = D(event.close) if event.status == 'observed' and not strategy.halted_reason else None
            if evaluation.intent:
                intent = evaluation.intent
                if intent.status == 'expired':
                    executions.append(dict(intent_key=intent.key, status='expired', reason=intent.expiry_reason, fill=None))
                else:
                    pending = intent
        else:
            quote_at = self.spec.calendar.sessions[event.session_index].close_at
            quote = None
        if kind == 'open' or evaluation.status != 'duplicate':
            # Never replace a more recent mark with an older close arriving late.
            # An unavailable current quote invalidates valuation instead of filling a gap.
            if timestamp(quote_at) <= now and (mark_at is None or timestamp(quote_at) >= timestamp(mark_at)):
                mark, mark_at = quote, quote_at
        if strategy.halted_reason:
            mark = None
        valuation = _valuation(book, day, self.spec.source.listing_id, mark, self.config)
        record = dict(event_hash=event_hash, kind=kind, decision_at=event.decision_at,
                      evaluation=evaluation.model_dump(mode='json') if evaluation else None,
                      executions=executions, valuation_price_at=mark_at, **valuation)
        self._strategy, self._pending, self._book, self._mark = strategy, pending, book, mark
        self._mark_at = mark_at
        self._last_open_index, self._last_open_hash = open_index, open_hash
        self._day, self._last_at, self._last_hash = day, event.decision_at, event_hash
        self._events.append(payload)
        self._records.append(record)
        if entry:
            self._journal.append(entry)
        return deepcopy(record)

    def report(self):
        with localcontext() as context:
            context.prec, context.rounding = 64, ROUND_HALF_EVEN
            valuation = _valuation(self._book, self._day, self.spec.source.listing_id, self._mark, self.config)
        executions = [outcome for row in self._records for outcome in row['executions']]
        return deepcopy(dict(format=SIMULATOR_VERSION, context_hash=self.context_hash,
            spec=self.spec.model_dump(mode='json'), config=self.config.model_dump(mode='json'),
            events=self._events, records=self._records, journal=self._journal, executions=executions,
            strategy_state=self._strategy.model_dump(mode='json'),
            pending_intent=self._pending.model_dump(mode='json') if self._pending else None,
            final={**valuation, 'valuation_price_at': self._mark_at},
            economic_scope='isolated-offline-account', external_orders=False))

    def checkpoint(self):
        payload = dict(format=SIMULATOR_VERSION, context_hash=self.context_hash, events=self._events)
        return json.dumps(dict(payload=payload, sha256=digest(payload)), sort_keys=True, separators=(',', ':'))


def restore_simulation(spec, config, document):
    if len(document.encode('utf-8')) > MAX_CHECKPOINT_BYTES:
        raise ValueError('Checkpoint económico demasiado grande.')
    envelope = json.loads(document)
    if not isinstance(envelope, dict) or set(envelope) != {'payload', 'sha256'}:
        raise ValueError('Formato de checkpoint económico desconocido.')
    payload = envelope['payload']
    if digest(payload) != envelope['sha256']:
        raise ValueError('Checkpoint económico corrupto.')
    simulation = SmaSimulation(spec, config)
    if not isinstance(payload, dict) or set(payload) != {'format', 'context_hash', 'events'}:
        raise ValueError('Contenido de checkpoint económico desconocido.')
    if payload['format'] != SIMULATOR_VERSION or payload['context_hash'] != simulation.context_hash:
        raise ValueError('El checkpoint pertenece a otra especificación o costes.')
    if not isinstance(payload['events'], list) or len(payload['events']) > MAX_EVENTS:
        raise ValueError('Historial económico demasiado largo o inválido.')
    for item in payload['events']:
        if not isinstance(item, dict) or set(item) != {'kind', 'observation'} or item['kind'] not in ('close', 'open'):
            raise ValueError('Evento económico desconocido.')
        model = CloseObservation if item['kind'] == 'close' else OpeningObservation
        simulation.process(model.model_validate_json(json.dumps(item['observation'])))
    return simulation


def simulate(spec, config, events):
    simulation = SmaSimulation(spec, config)
    for event in events:
        simulation.process(event)
    return simulation

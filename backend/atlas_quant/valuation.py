"""Pure D6 close valuation. No provider calls, persistence or implicit FX trades."""
from bisect import bisect_right
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext, ROUND_HALF_EVEN

from .book import balance, NativeBook, decimal_text, bounded, CENT
from .quality import timestamp

ORDER = {'complete': 0, 'provisional': 1, 'incomplete': 2}


def worst(*states):
    return max(states, key=ORDER.get, default='complete')


def missing(code):
    return dict(status='incomplete', value=None, series_id=None, version=None, sha256=None, source=None,
                date=None, age_days=None, available_at=None, historical_known=False, reasons=[code], historical_reasons=[code])


class MarkSeries:
    """One index per immutable series; selection never uses a future observation."""
    def __init__(self, dataset, symbol, kind='prices'):
        self.dataset, self.kind = dataset, kind
        self.bars = sorted((b for b in dataset['bars'] if b['symbol'] == symbol), key=lambda b: b['date'])
        self.dates = [b['date'] for b in self.bars]
        self.evidence = dataset.get('quality_evidence', {}).get(symbol, {})
        self.calendar = self.evidence.get('calendar') or {}
        self.days = self.calendar.get('days', {})
        self.opens = sorted(k for k, v in self.days.items() if v['status'] == 'open')

    def select(self, day, decision_at):
        result = missing('missing_fx' if self.kind == 'fx' else 'missing_price')
        result.update(series_id=self.dataset['id'], version=self.dataset['version'], source=self.dataset['source'],
                      sha256=self.dataset.get('sha256') or self.dataset.get('manifest', {}).get('sha256'))
        index = bisect_right(self.dates, day) - 1
        if index < 0:
            return result
        bar = self.bars[index]
        age = (date.fromisoformat(day) - date.fromisoformat(bar['date'])).days
        available = bar.get('available_at') or self.evidence.get('availability', {}).get(bar['date'])
        historic = [] if available and timestamp(available) <= timestamp(decision_at) else ['availability_unknown' if not available else 'available_after_decision']
        status, reasons = 'complete', []
        expected_index = bisect_right(self.opens, day) - 1
        expected = self.opens[expected_index] if expected_index >= 0 else None
        verified = self.calendar.get('verified') is True
        if verified and self.days.get(bar['date'], {}).get('status') == 'closed':
            status, reasons = 'incomplete', ['unexpected_bar']
        elif not (verified and day in self.days and expected == bar['date']):
            status = 'provisional' if age <= 7 else 'incomplete'
            reasons = ['calendar_unknown' if not verified or day not in self.days else 'missing_session']
            if age > 7:
                reasons.append('stale_mark')
        if self.kind == 'prices' and (self.evidence.get('price_basis') != 'raw' or self.evidence.get('basis_verified') is not True):
            status = 'incomplete'
            reasons.append('price_basis_incompatible')
        value = str(bar['rate' if self.kind == 'fx' else 'close'])
        result.update(status=status, value=value if status != 'incomplete' else None, date=bar['date'], age_days=age,
                      available_at=available, historical_known=not historic, reasons=reasons, historical_reasons=historic)
        return result


class Valuator:
    def __init__(self, context):
        self.context = context
        datasets = {(d['id'], d['version']): d for d in context['datasets']}
        self.prices = {b['listing_id']: MarkSeries(datasets[(b['dataset_id'], b['dataset_version'])], b['symbol'])
                       for b in context['portfolio']['bindings'] if (b['dataset_id'], b['dataset_version']) in datasets}
        self.fx = MarkSeries(context['fx'], 'USD_EUR', 'fx') if context['fx'] else None
        self.entries = sorted(context['entries'], key=lambda e: (e['date'], e['day_sequence']))
        self.entry_dates = [e['date'] for e in self.entries]
        self._cursor, self._index = NativeBook(), 0
        self._last_book = None
        self.payment_dates = {e['event'].get('external_key'): e['date'] for e in self.entries}

    def fx_mark(self, day, decision_at):
        return self.fx.select(day, decision_at) if self.fx else missing('missing_fx')

    def book(self, day):
        index = bisect_right(self.entry_dates, day)
        if index < self._index:
            self._cursor, self._index, self._last_book = NativeBook(), 0, None
        if index != self._index or self._last_book is None:
            for entry in self.entries[self._index:index]:
                self._cursor.apply(entry)
            self._index = index
            self._last_book = self._cursor.snapshot(day)
        return {**self._last_book, 'as_of_date': day}

    def flows(self, end, start=None):
        result = []
        with localcontext() as precision:
            precision.prec, precision.rounding = 64, ROUND_HALF_EVEN
            for item in self.entries:
                event = item['event']
                if item['date'] > end or (start is not None and item['date'] <= start) or event['kind'] not in ('deposit', 'withdrawal'):
                    continue
                native = Decimal(event['gross_amount']) * (1 if event['kind'] == 'deposit' else -1)
                fx = self.fx_mark(item['date'], item['date']+'T23:59:59.999999+00:00') if event['currency'] == 'USD' else None
                converted = native * Decimal(fx['value']) if fx and fx['value'] is not None else (native if fx is None else None)
                if converted is not None:
                    bounded(converted, 'external_flow_eur')
                result.append(dict(event_id=event['id'], date=item['date'], currency=event['currency'], native_amount=decimal_text(native),
                    eur_amount=decimal_text(converted) if converted is not None else None, status=fx['status'] if fx else 'complete', fx=fx))
        return result

    def cut(self, day, decision_at=None, *, include_flows=True):
        decision_at = timestamp(decision_at or day+'T23:59:59.999999+00:00').isoformat()
        book, components, problems, historical = self.book(day), [], [], []
        context = self.context
        fx = self.fx_mark(day, decision_at)
        with localcontext() as precision:
            precision.prec, precision.rounding = 64, ROUND_HALF_EVEN
            def component(kind, reference, currency, native, quantity=None, price=None, reasons=None):
                conversion = fx if currency == 'USD' and native != 0 else None
                state = worst(price['status'] if price else 'complete', conversion['status'] if conversion else 'complete')
                notes = list(reasons or []) + (price['reasons'] if price else []) + (conversion['reasons'] if conversion else [])
                if reasons:
                    state = 'incomplete'
                value = native if not conversion else (native * Decimal(conversion['value']) if native is not None and conversion['value'] is not None else None)
                if state == 'incomplete':
                    value = None
                if value is not None:
                    bounded(value, 'component_eur')
                for mark in (price, conversion):
                    if mark:
                        historical.extend(mark['historical_reasons'])
                components.append(dict(kind=kind, reference=reference, currency=currency, quantity=quantity,
                    native_value=decimal_text(native) if native is not None else None,
                    eur_value=decimal_text(value) if value is not None else None,
                    display_eur=decimal_text(value.quantize(CENT), money=True) if value is not None else None,
                    status=state, price=price, fx=conversion, reasons=sorted(set(notes))))

            for b in book['balances']:
                component('cash', b['currency'], b['currency'], Decimal(b['cash']))
            events = {e['id']: e for e in context['corporate']['events']}
            apps = {a['event_id']: a for a in context['applications'] if a['effective_date'] <= day}
            split_dates = {}
            for app in apps.values():
                if app['cancelled']:
                    continue
                event = app['event_snapshot']
                valid = events.get(app['event_id'], {}).get('revision') == app['event_revision'] and event['verified']
                if not valid:
                    problems.append('corporate_action_unresolved')
                available = event.get('available_at')
                if not available or timestamp(available) > timestamp(decision_at):
                    historical.append('corporate_availability_unknown' if not available else 'corporate_available_after_decision')
                payment_date = self.payment_dates.get(app['movement_key'])
                if event['event_type'] == 'dividend' and (payment_date is None or payment_date > day):
                    component('receivable', app['event_id'], event['currency'], Decimal(app['gross_amount']),
                              reasons=[] if valid else ['corporate_action_unresolved'])
                if event['event_type'] == 'split':
                    split_dates[event['listing_id']] = max(split_dates.get(event['listing_id'], ''), app['effective_date'])
            for p in book['positions']:
                series = self.prices.get(p['listing_id'])
                mark = series.select(day, decision_at) if series else missing('missing_price')
                reasons = ['corporate_action_unresolved'] if (p['listing_id'] in split_dates and (not mark['date'] or mark['date'] < split_dates[p['listing_id']])) else []
                native = Decimal(p['quantity']) * Decimal(mark['value']) if mark['value'] is not None else None
                component('position', p['listing_id'], p['currency'], native, p['quantity'], mark, reasons)
            # A known but unapplied event cannot silently disappear from NAV.
            for event in events.values():
                effective = event.get('effective_date')
                app = apps.get(event['id'])
                if event['cancelled'] or (effective and effective > day) or (app and not app['cancelled']):
                    continue
                if not effective:
                    if any(e['listing_id'] == event['listing_id'] and e['date'] <= day for e in self.entries):
                        problems.append('corporate_action_unresolved')
                    continue
                before = [e for e in self.entries if e['date'] < effective]
                held = balance(before, effective, multicurrency=True)['positions']
                same_day = any(e['listing_id'] == event['listing_id'] and e['date'] == effective for e in self.entries)
                if same_day or any(p['listing_id'] == event['listing_id'] for p in held):
                    problems.append('corporate_action_unresolved')
            status = worst(*(c['status'] for c in components), 'incomplete' if problems else 'complete')
            known = bounded(sum((Decimal(c['eur_value']) for c in components if c['eur_value'] is not None), Decimal(0)), 'nav_eur')
            rounded = known.quantize(CENT)
            displays = sum((Decimal(c['display_eur']) for c in components if c['display_eur'] is not None), Decimal(0))
            reasons = sorted(set(problems + [r for c in components for r in c['reasons']]))
            return dict(policy='atlas-nav-v1', mode='reconstruction_at_close', as_of_date=day, decision_at=decision_at,
                status=status, value=decimal_text(rounded, money=True) if status != 'incomplete' else None,
                exact_value=decimal_text(known) if status != 'incomplete' else None, known_subtotal=decimal_text(rounded, money=True),
                rounding_difference=decimal_text(rounded-displays, money=True), balance=book, components=components,
                flows=self.flows(day) if include_flows else [], reasons=reasons, historical_known=not historical and status != 'incomplete',
                historical_reasons=sorted(set(historical + (['reconstruction_incomplete'] if status == 'incomplete' else []))))

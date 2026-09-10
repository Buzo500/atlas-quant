"""Pure exposure/limit diagnosis consuming a D6 cut, never recalculating a book."""
from decimal import Decimal, localcontext
from .book import decimal_text

POLICY = 'atlas-targets-v1'


def limits(weight, minimum, maximum, concentration_limit):
    """Percent inputs; applicable to future target proposals without authority to send."""
    reasons = []
    if weight < minimum:
        reasons.append('below_band')
    if weight > maximum:
        reasons.append('above_band')
    if weight > concentration_limit:
        reasons.append('concentration_exceeded')
    return reasons


def evaluate(cut, spec, catalog, corporate):
    with localcontext() as ctx:
        ctx.prec = 60
        listings = {l['id']: l['instrument_id'] for l in catalog['listings']}
        names = {i['id']: i['name'] for i in catalog['instruments']}
        events = {e['id']: e['listing_id'] for e in corporate['events']}
        targets = {r['instrument_id']: r for r in spec['rows']}
        values = {ident: Decimal(0) for ident in targets}
        rights = {}
        missing = set()
        cash = []
        for c in cut['components']:
            if c['kind'] == 'cash':
                ident = None
                cash.append(dict(currency=c['currency'], native_amount=c['native_value'], eur_value=c['eur_value']))
            else:
                listing = events.get(c['reference']) if c['kind'] == 'receivable' else c['reference']
                if listing not in listings:
                    raise ValueError('El corte contiene una referencia sin identidad de instrumento.')
                ident = listings[listing]
            values.setdefault(ident, Decimal(0))
            if c['eur_value'] is None:
                missing.add(ident)
            else:
                value = Decimal(c['eur_value'])
                values[ident] += value
                if c['kind'] == 'receivable':
                    rights[ident] = rights.get(ident, Decimal(0)) + value
        nav = Decimal(cut['exact_value']) if cut['exact_value'] is not None else None
        reasons = list(cut['reasons'])
        usable = cut['status'] != 'incomplete' and nav is not None and nav > 0 and not missing
        if nav is not None and nav <= 0:
            reasons.append('non_positive_nav')
        rows = []
        for ident in sorted(values, key=lambda i: (i is None, i or '')):
            t = targets.get(ident)
            target = Decimal(t['weight']) if t else Decimal(0)
            value = values[ident]
            weight = value / nav * 100 if usable else None
            row_reasons = [] if t else ['no_target']
            if t and weight is not None:
                row_reasons += limits(weight, Decimal(t['minimum']), Decimal(t['maximum']), Decimal(t['concentration_limit']))
            rows.append(dict(instrument_id=ident, label=names[ident] if ident else 'Efectivo',
                value_eur=None if ident in missing else decimal_text(value),
                receivable_eur=None if ident in missing else decimal_text(rights.get(ident, Decimal(0))),
                weight=decimal_text(weight) if weight is not None else None,
                target_weight=decimal_text(target), minimum=t['minimum'] if t else None,
                maximum=t['maximum'] if t else None, concentration_limit=t['concentration_limit'] if t else None,
                deviation_pp=decimal_text(weight-target) if usable else None,
                deviation_eur=decimal_text(value-nav*target/100) if usable else None, reasons=row_reasons))
        return dict(policy=POLICY, status=cut['status'] if usable else 'unavailable', reasons=sorted(set(reasons)),
            rows=rows, resources=dict(cash=cash, committed=None, reservation_status='not_implemented'))

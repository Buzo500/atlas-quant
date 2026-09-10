"""D7 pure period attribution and bounded, uniqueness-gated XIRR."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from math import exp, fsum, isfinite, log1p

from .book import CENT, bounded, decimal_text, cutoff, BookError
from .valuation import Valuator, worst

POLICY = 'atlas-performance-v1'
MAX_DAYS = 3660
LOW, HIGH, TOLERANCE = -0.999999, 1000.0, 1e-10


def metric(value, status='complete', reasons=()):
    if value is not None and (not value.is_finite() or abs(value) > Decimal('1e18')):
        value, status, reasons = None, 'unavailable', [*reasons, 'numeric_range']
    return dict(value=decimal_text(value) if value is not None else None, status=status, reasons=sorted(set(reasons)))


def xirr(flows):
    """Actual/365, grouped civil dates; publish only a proved unique pattern.

    Accounting remains Decimal. The scalar solver uses normalized double
    precision with fsum and reports both bracket width and original residual.
    """
    grouped = defaultdict(Decimal)
    for day, value in flows:
        grouped[day] += Decimal(value)
    items = sorted((date.fromisoformat(d), v) for d, v in grouped.items() if v)
    result = dict(value=None, status='unavailable', reasons=[], convention='actual-days/365',
        domain=[str(LOW), str(HIGH)], iterations=0, bracket_width=None, normalized_residual=None,
        rate_tolerance=str(TOLERANCE), residual_tolerance=str(TOLERANCE), max_iterations=200)
    def unavailable(reason):
        return dict(result, reasons=[reason])
    if len({d for d,_ in flows}) < 2:
        return unavailable('no_duration' if flows else 'no_investment')
    if not any(v < 0 for _, v in items):
        return unavailable('no_investment')
    if not any(v > 0 for _, v in items):
        return unavailable('no_positive_recovery')
    positive = False
    for _, value in items:
        if value > 0:
            positive = True
        elif positive:
            return unavailable('unsupported_cashflow_pattern')
    scale = max(Decimal(1), sum(abs(v) for _, v in items))
    coefficients = [float(v/scale) for _, v in items]
    times = [(d-items[0][0]).days/365 for d, _ in items]
    def value(rate):
        return fsum(c*exp(-t*log1p(rate)) for c, t in zip(coefficients, times))
    left, right = LOW, HIGH
    try:
        a, b = value(left), value(right)
        if not isfinite(a) or not isfinite(b):
            return unavailable('numeric_range')
        if a < 0 or b > 0:
            return unavailable('out_of_domain')
        for step in range(1, 201):
            middle = left+(right-left)/2
            residual = value(middle)
            result.update(iterations=step, bracket_width=str(right-left), normalized_residual=str(abs(residual)))
            if right-left <= TOLERANCE and abs(residual) <= TOLERANCE:
                return dict(result, value=str(middle), status='complete')
            if middle == left or middle == right:
                break
            if residual > 0:
                left = middle
            else:
                right = middle
    except (OverflowError, ValueError):
        return unavailable('numeric_range')
    return unavailable('no_convergence')


def costs(valuator, start, end):
    result = []
    for entry in valuator.entries:
        if not start < entry['date'] <= end:
            continue
        event = entry['event']
        components = [('fee', event['fee_amount'], event.get('fee_currency') or event['currency']),
                      ('tax', event.get('tax_amount') or '0', event.get('tax_currency') or event['currency'])]
        if event['kind'] == 'fee':
            components.append(('charge', event['gross_amount'], event['currency']))
        for kind, text, currency in components:
            native = Decimal(text or '0')
            if not native:
                continue
            fx = valuator.fx_mark(entry['date'], entry['date']+'T23:59:59.999999+00:00') if currency == 'USD' else None
            value = native if fx is None else (native*Decimal(fx['value']) if fx['value'] is not None else None)
            result.append(dict(event_id=event['id'], date=entry['date'], kind=kind, currency=currency,
                native_amount=decimal_text(native), eur_amount=decimal_text(bounded(value, 'cost_eur')) if value is not None else None,
                status=fx['status'] if fx else 'complete', fx=fx))
    return result


def twr(points):
    segments, current = [], None
    problems = []
    for previous, point in zip(points, points[1:]):
        values = previous['nav_exact'], point['nav_exact'], point['flow_eur']
        factor = None
        if all(v is not None for v in values) and Decimal(values[0]) > 0:
            factor = (Decimal(values[1])-Decimal(values[2]))/Decimal(values[0])
            if factor < 0:
                factor = None
                problems.append('negative_daily_factor')
        if factor is None:
            if current:
                segments.append(current)
                current = None
            point['twr_factor'] = None
            continue
        if current is None:
            current = dict(start_date=previous['date'], end_date=point['date'], factor=Decimal(1), status=previous['status'])
        current['factor'] *= factor
        current.update(end_date=point['date'], status=worst(current['status'], point['status']))
        point['twr_factor'] = decimal_text(factor)
    if current:
        segments.append(current)
    result = metric(None, 'unavailable', problems or ['discontinuous_nav'])
    result.update(convention='daily-external-flows-at-close', start_date=None, end_date=points[-1]['date'], segments=[])
    for segment in segments:
        result['segments'].append(dict(start_date=segment['start_date'], end_date=segment['end_date'],
            **metric(segment['factor']-1, segment['status'])))
    if len(segments) == 1 and segments[0]['start_date'] == points[0]['date'] and segments[0]['end_date'] == points[-1]['date']:
        result.update(metric(segments[0]['factor']-1, segments[0]['status']), start_date=segments[0]['start_date'])
    return result


def calculate(context, start, end):
    start, end = cutoff(start), cutoff(end)
    duration = (date.fromisoformat(end)-date.fromisoformat(start)).days
    if duration <= 0 or duration > MAX_DAYS:
        raise BookError('period_limit', f'Elige un periodo entre cierres de 1 a {MAX_DAYS} días.')
    with localcontext() as precision:
        precision.prec, precision.rounding = 64, ROUND_HALF_EVEN
        valuator = Valuator(context)
        flows = valuator.flows(end, start)
        charges = costs(valuator, start, end)
        daily_flows = defaultdict(list)
        for flow in flows:
            daily_flows[flow['date']].append(flow)
        linked = {a['movement_key'] for a in context['applications'] if not a['cancelled']}
        # Without a known ex-date, a later payment can affect any earlier held period.
        unlinked = [e['event']['id'] for e in valuator.entries if e['event']['kind'] == 'dividend_payment'
                    and e['date'] > start and e['event']['external_key'] not in linked
                    and any(old['listing_id'] == e['listing_id'] and old['date'] <= end for old in valuator.entries)]
        points, endpoints = [], []
        for offset in range(duration+1):
            day = (date.fromisoformat(start)+timedelta(days=offset)).isoformat()
            cut = valuator.cut(day, include_flows=False)
            if offset in (0, duration):
                endpoints.append(cut)
            day_flows = daily_flows[day]
            complete_flow = all(f['eur_amount'] is not None for f in day_flows)
            flow_value = sum((Decimal(f['eur_amount']) for f in day_flows), Decimal(0)) if complete_flow else None
            points.append(dict(date=day, nav=cut['value'], nav_exact=cut['exact_value'],
                flow_eur=decimal_text(flow_value) if flow_value is not None else None,
                status=worst(cut['status'], *(f['status'] for f in day_flows)), twr_factor=None,
                historical_known=cut['historical_known'] and all(not f['fx'] or f['fx']['historical_known'] for f in day_flows),
                reasons=sorted(set(cut['reasons']+(['missing_flow_fx'] if not complete_flow else [])))))
        initial, final = endpoints
        flow_status = worst(*(f['status'] for f in flows))
        status = worst(initial['status'], final['status'], flow_status, 'incomplete' if unlinked else 'complete')
        reasons = initial['reasons']+final['reasons']+(['missing_flow_fx'] if flow_status == 'incomplete' else [])+(['unlinked_dividend_history'] if unlinked else [])
        net = sum((Decimal(f['eur_amount']) for f in flows), Decimal(0)) if flow_status != 'incomplete' else None
        pnl = bounded(Decimal(final['exact_value'])-Decimal(initial['exact_value'])-net, 'pnl_eur') if status != 'incomplete' else None
        gain = metric(pnl, status, reasons)
        gain['display_value'] = decimal_text(pnl.quantize(CENT), money=True) if pnl is not None else None
        weighted = xirr([(start, -Decimal(initial['exact_value']))]+[(f['date'], -Decimal(f['eur_amount'])) for f in flows]+[(end, Decimal(final['exact_value']))]) if status != 'incomplete' else xirr([])
        if status == 'incomplete':
            weighted.update(value=None, status='unavailable', reasons=sorted(set(reasons)))
        elif weighted['value'] is not None:
            weighted['status'] = status
        time_weighted = twr(points)
        if unlinked:
            time_weighted.update(value=None, status='unavailable', reasons=['unlinked_dividend_history'])
            for point in points:
                point['twr_factor'] = None
            for segment in time_weighted['segments']:
                segment.update(value=None, status='unavailable', reasons=['unlinked_dividend_history'])
        cost_status = worst(*(c['status'] for c in charges))
        total_cost = sum((Decimal(c['eur_amount']) for c in charges), Decimal(0)) if cost_status != 'incomplete' else None
        return dict(policy=POLICY, start_date=start, end_date=end, initial_nav=initial['value'], final_nav=final['value'],
            external_net=metric(net, flow_status, ['missing_flow_fx'] if net is None else []), pnl=gain, twr=time_weighted, mwr=weighted,
            costs=charges, costs_eur=metric(total_cost, cost_status, ['missing_cost_fx'] if total_cost is None else []),
            flows=flows, points=points, unlinked_payments=unlinked,
            historical_known=all(p['historical_known'] for p in points) and not unlinked,
            source_context={**context['stamp'], 'price_heads':[dict(series_id=k,version=v) for k,v in context['stamp']['price_heads']]})

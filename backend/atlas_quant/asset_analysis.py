"""Pure price comparisons. No interpolation, cash movements or portfolio returns."""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from statistics import stdev
from .valuation import MarkSeries
from .book import decimal_text

POLICY = 'atlas-asset-analysis-v1'
MIN_OBSERVATIONS = 20
ANNUAL_SESSIONS = 252
ZERO, ONE, HUNDRED = Decimal(0), Decimal(1), Decimal(100)


def statistic(value):
    if value is None:
        return None
    return decimal_text(value.quantize(Decimal('0.000000000001'), rounding=ROUND_HALF_EVEN))


def profile(source, dataset, fx, corporate, start, end):
    series = MarkSeries(dataset, source['ref']['symbol'])
    bars = {b['date']: b for b in series.bars if start <= b['date'] <= end}
    expected = [d for d in series.opens if start <= d <= end]
    reasons, values = set(), {}
    calendar = series.calendar
    eligible = True
    if not (calendar.get('verified') and calendar.get('start', end) <= start and calendar.get('end', start) >= end):
        reasons.add('calendar_unverified_or_outside_coverage')
        eligible = False
    if series.evidence.get('price_basis') != 'raw' or series.evidence.get('basis_verified') is not True:
        reasons.add('raw_price_basis_required')
        eligible = False
    events = [e for e in corporate['events'] if e['listing_id'] == source['listing_id'] and not e['cancelled']]
    splits = [e for e in events if e['event_type'] == 'split' and
              (not e.get('effective_date') or start < e['effective_date'] <= end)]
    legacy_events = [e for e in dataset.get('corporate_actions', []) if e.get('symbol') == source['ref']['symbol']
                     and start < e.get('date', end) <= end]
    if splits or any(e.get('kind') == 'split' for e in legacy_events):
        reasons.add('known_corporate_adjustment_required')
        eligible = False
    historic = True
    if eligible:
        for day in expected:
            if day not in bars:
                reasons.add('missing_price_session')
                continue
            cut = day+'T23:59:59.999999+00:00'
            mark = series.select(day, cut)
            if mark['status'] != 'complete' or not mark['historical_known']:
                reasons.update(mark['reasons'] + mark['historical_reasons'])
                historic = historic and mark['historical_known']
                continue
            value = Decimal(mark['value'])
            if source['currency'] == 'USD':
                if fx is None:
                    reasons.add('missing_fx_series')
                    continue
                conversion = fx.select(day, cut)
                if conversion['date'] != day or conversion['status'] != 'complete' or not conversion['historical_known']:
                    reasons.add('missing_same_date_fx')
                    reasons.update(conversion['reasons'] + conversion['historical_reasons'])
                    historic = historic and conversion['historical_known']
                    continue
                value *= Decimal(conversion['value'])
            values[day] = value
    if set(bars)-set(expected):
        reasons.add('unexpected_price_session')
    intervals = {(a,b): values[b]/values[a]-ONE for a,b in zip(expected,expected[1:]) if a in values and b in values}
    complete = eligible and len(expected) >= 2 and len(values) == len(expected) and not reasons
    if len(expected) < 2:
        reasons.add('insufficient_sessions')
    change = session_vol = annual_vol = drawdown = None
    if complete:
        ordered = [values[d] for d in expected]
        change = (ordered[-1]/ordered[0]-ONE)*HUNDRED
        peak, drawdown = ordered[0], ZERO
        for value in ordered:
            peak = max(peak,value)
            drawdown = min(drawdown,value/peak-ONE)
        drawdown *= HUNDRED
        if len(intervals) >= 2:
            session_vol = stdev(intervals.values())*HUNDRED
            annual_vol = session_vol*Decimal(ANNUAL_SESSIONS).sqrt()
    last = max(bars) if bars else None
    result = dict(source=source,status='complete' if complete else ('partial' if values else 'unavailable'),
        reasons=sorted(reasons),expected_sessions=len(expected),observed_sessions=len(bars),valid_sessions=len(values),
        valid_intervals=len(intervals),first_date=min(bars) if bars else None,last_date=last,
        last_close_native=str(bars[last]['close']) if last else None,last_close_eur=decimal_text(values[last]) if last in values else None,
        price_change_pct=statistic(change),session_volatility_pct=statistic(session_vol),
        annualized_volatility_pct=statistic(annual_vol),max_drawdown_pct=statistic(drawdown),
        historical_known=historic and complete,known_dividends=sum(e['event_type']=='dividend' and start < (e.get('effective_date') or '') <= end for e in events))
    return result, values, intervals


def compare(prepared):
    dates = sorted(set.intersection(*(set(values) for _,values,_ in prepared)))
    if len(dates) < 2:
        return dict(start_date=None,end_date=None,rows=[],points=[],reasons=['insufficient_common_dates'])
    first, last = dates[0], dates[-1]
    rows = [dict(source_key=p['source']['key'],start_eur=decimal_text(v[first]),end_eur=decimal_text(v[last]),
                 price_change_pct=statistic((v[last]/v[first]-ONE)*HUNDRED)) for p,v,_ in prepared]
    points = [dict(date=d,indices=[statistic(v[d]/v[first]*HUNDRED) for _,v,_ in prepared]) for d in dates]
    reasons = ['common_observed_dates_only']
    if any(p['status']!='complete' for p,_,_ in prepared):
        reasons.append('partial_source_coverage')
    return dict(start_date=first,end_date=last,rows=rows,points=points,reasons=reasons)


def correlations(prepared):
    common = sorted(set.intersection(*(set(intervals) for _,_,intervals in prepared)))
    samples = [[intervals[key] for key in common] for _,_,intervals in prepared]
    means = [sum(row,ZERO)/len(row) for row in samples] if common else [ZERO for _ in samples]
    centered = [[v-mean for v in row] for row,mean in zip(samples,means)]
    squares = [sum((v*v for v in row),ZERO) for row in centered]
    cells = []
    for i,(left,_,_) in enumerate(prepared):
        for j,(right,_,_) in enumerate(prepared):
            value, reason = None, None
            if len(common) < MIN_OBSERVATIONS:
                reason = 'insufficient_common_intervals'
            elif squares[i] == 0 or squares[j] == 0:
                reason = 'constant_return_series'
            else:
                value = sum((x*y for x,y in zip(centered[i],centered[j])),ZERO)/(squares[i]*squares[j]).sqrt()
                value = max(-ONE,min(ONE,value))
            cells.append(dict(left=left['source']['key'],right=right['source']['key'],value=statistic(value),reason=reason))
    return dict(method='pearson-simple-returns',minimum_observations=MIN_OBSERVATIONS,observations=len(common),
                intervals=[dict(start_date=a,end_date=b) for a,b in common],cells=cells,
                reasons=['listwise_identical_session_intervals'] + (['partial_source_coverage'] if any(p['status']!='complete' for p,_,_ in prepared) else []))


def calculate(sources, fx_data, fx_source, corporate, body):
    with localcontext() as context:
        context.prec = 64
        fx = MarkSeries(fx_data,'USD_EUR','fx') if fx_data else None
        prepared = [profile(source,data,fx,corporate,body.start_date,body.end_date) for source,data in sources]
        return dict(profiles=[p for p,_,_ in prepared],comparison=compare(prepared),correlations=correlations(prepared),
            fx=fx_source,currency='EUR',basis='raw-price-excluding-dividends',annualization_sessions=ANNUAL_SESSIONS,
            warnings=['price_return_excludes_dividends_and_costs','no_inferred_corporate_events','historical_correlation_not_forecast'])

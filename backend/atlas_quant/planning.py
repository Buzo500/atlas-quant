"""Deterministic analytical policies sharing D6 marks and the target risk reducer."""
from copy import deepcopy
import csv
import re
from datetime import date
from decimal import Decimal as D, localcontext, ROUND_DOWN, ROUND_UP
from hashlib import sha256
from io import StringIO
from .book import decimal_text as text
from .targets import evaluate
from .targets_contracts import TargetSpec

POLICY = 'atlas-planning-v1'
ZERO = D(0)
HUNDRED = D(100)


def combine(active, contributors):
    """Each strategy owns only its budget; global active bands remain authoritative."""
    with localcontext() as ctx:
        ctx.prec = 60
        rows = {r['instrument_id']: dict(r, weight='0') for r in active['spec']['rows']}
        weights = {i: ZERO for i in rows}
        used = sum((D(c['budget']) for c in contributors), ZERO)
        if used > 100:
            raise ValueError('Presupuestos superiores al patrimonio disponible.')
        weights[None] = 100-used
        for c in contributors:
            for r in c['target']['spec']['rows']:
                if r['instrument_id'] not in rows and D(r['weight']) != 0:
                    raise ValueError('Una estrategia incluye un instrumento sin límites globales. Revisa los objetivos activos.')
                if r['instrument_id'] in rows:
                    weights[r['instrument_id']] += D(c['budget'])*D(r['weight'])/100
        remainder = ZERO
        for ident, value in weights.items():
            if ident is not None:
                rounded = value.quantize(D('.000001'), rounding=ROUND_DOWN)
                rows[ident]['weight'] = text(rounded)
                remainder += value-rounded
        rows[None]['weight'] = text(weights[None]+remainder)
        try:
            spec = TargetSpec(name='Objetivos combinados por presupuesto', rows=list(rows.values())).model_dump()
        except ValueError as exc:
            raise ValueError('La combinación incumple las bandas o límites globales activos. Ajusta los presupuestos o revisa esos límites explícitamente.') from exc
        return dict(spec=spec, contributors=contributors, unassigned_budget=text(100-used),
                    rounding_cash_pp=text(remainder), reasons=[])


def scenario(cut, target, catalog, corporate, body):
    with localcontext() as ctx:
        ctx.prec = 60
        changed = deepcopy(cut)
        shocks = {s.instrument_id: D(s.change_percent)/100+1 for s in body.price_shocks}
        listings = {l['id']: l['instrument_id'] for l in catalog['listings']}
        if set(shocks)-set(listings.values()):
            raise ValueError('El escenario referencia un instrumento inexistente.')
        fx_factor = 1+D(body.usd_eur_change_percent)/100
        for c in changed['components']:
            factor = fx_factor if c['currency'] == 'USD' else D(1)
            if c['kind'] == 'position':
                factor *= shocks.get(listings[c['reference']], D(1))
            if c['eur_value'] is not None:
                c['eur_value'] = text(D(c['eur_value'])*factor)
        before = D(cut['exact_value']) if cut['exact_value'] is not None else None
        after = sum((D(c['eur_value']) for c in changed['components']), ZERO) if before is not None else None
        changed['exact_value'] = text(after) if after is not None else None
        result = evaluate(changed, target['spec'], catalog, corporate)
        return dict(kind='scenario', cut=cut, target=target, nav_before=text(before) if before is not None else None,
            nav_after=text(after) if after is not None else None,
            change_eur=text(after-before) if after is not None else None,
            status=result['status'], rows=result['rows'], reasons=result['reasons'])


def benchmark(performance, body):
    """Comparable total-return series only, same dates and EUR base; never interpolate."""
    if performance['twr']['value'] is None or performance['twr']['status'] not in ('complete','provisional'):
        raise ValueError('El informe necesita TWR continuo disponible para comparar.')
    reader = csv.DictReader(StringIO(body.benchmark_csv.lstrip('\ufeff')), strict=True)
    if reader.fieldnames != ['date', 'value']:
        raise ValueError('El CSV de referencia debe tener exactamente las columnas date,value.')
    values = {}
    try:
        for row in reader:
            if len(values) >= 3661 or None in row or row['date'] in values:
                raise ValueError('CSV demasiado largo, fila irregular o fecha duplicada.')
            day = date.fromisoformat(row['date']).isoformat()
            if row['value'] is None or not re.fullmatch(r'(?:0|[1-9]\d{0,14})(?:\.\d{1,12})?',row['value']):
                raise ValueError('Usa valores decimales positivos, hasta 15 cifras enteras y 12 decimales; sin exponentes.')
            value = D(row['value'])
            if day != row['date'] or not 0 < value <= D('1e15'):
                raise ValueError('Fecha o valor de referencia inválidos.')
            values[day] = value
    except (csv.Error, ArithmeticError, TypeError) as exc:
        raise ValueError('CSV de referencia inválido.') from exc
    dates = [p['date'] for p in performance['points']]
    if not dates or set(dates) != set(values) or performance['start_date'] != dates[0] or performance['end_date'] != dates[-1]:
        raise ValueError('El CSV debe cubrir exactamente todas las fechas del informe, incluidos sus cierres inicial y final. No se rellenan huecos.')
    if performance['twr'].get('start_date') != performance['start_date'] or any(p['twr_factor'] is None for p in performance['points'][1:]):
        raise ValueError('La curva TWR contiene puntos sin rentabilidad comparable.')
    with localcontext() as ctx:
        ctx.prec = 60
        factor = D(1)
        points = []
        for index,p in enumerate(performance['points']):
            if index: factor *= D(p['twr_factor'])
            points.append(dict(date=p['date'],portfolio_index=text(factor*100),
                benchmark_index=text(values[p['date']]/values[dates[0]]*100)))
        portfolio_return = D(points[-1]['portfolio_index'])/100-1
        benchmark_return = values[dates[-1]]/values[dates[0]]-1
        return dict(kind='benchmark', performance_id=performance['id'], name=body.benchmark_name.strip(),
            source=body.benchmark_source.strip(), csv_sha256=sha256(body.benchmark_csv.encode()).hexdigest(),
            basis='total-return-EUR', evidence='user_declared', start_date=dates[0], end_date=dates[-1],
            status=performance['twr']['status'], portfolio_return=text(portfolio_return), benchmark_return=text(benchmark_return),
            excess_pp=text((portfolio_return-benchmark_return)*100), points=points)


def allocation(cut, target, combined, catalog, corporate, body, market):
    spec = combined['spec'] if combined else target['spec']
    return dict(kind='allocation', cut=cut, target=target, combined=combined,
        variants=[_variant(cut, spec, catalog, corporate, body, market, mode) for mode in ('contributions','rebalance')],
        reservation_status='not_implemented', sale_proceeds='hypothetical_settled')


def _variant(cut, spec, catalog, corporate, body, market, mode):
    with localcontext() as ctx:
        ctx.prec = 60
        diagnosis = evaluate(cut, spec, catalog, corporate)
        result = dict(mode=mode, status='unavailable', provisional=cut['status']=='provisional', reasons=[],
                      trades=[], cash=[], costs_eur='0', nav_after=None, rows=diagnosis['rows'])
        if diagnosis['status'] == 'unavailable':
            return dict(result, reasons=diagnosis['reasons'] or ['Patrimonio no disponible.'])
        changed = deepcopy(cut)
        cash = {c: ZERO for c in ('EUR','USD')}
        for c in cut['components']:
            if c['kind']=='cash': cash[c['currency']] += D(c['native_value'])
        initial = dict(cash)
        contributions = dict(EUR=D(body.contribution_eur), USD=D(body.contribution_usd))
        fx = market['fx']
        rate = D(fx['value']) if fx and fx['value'] is not None else None
        if (contributions['USD'] or cash['USD']) and rate is None:
            return dict(result, reasons=['Falta FX USD/EUR para los recursos de la simulación.'])
        rates = dict(EUR=D(1), USD=rate)
        spendable = {c: (cash[c] if body.use_existing_cash else ZERO)+contributions[c] for c in cash}
        cash = {c: cash[c]+contributions[c] for c in cash}
        if any(v<0 for v in cash.values()):
            return dict(result, reasons=['La simulación no admite efectivo negativo ni préstamos.'])
        nav = D(cut['exact_value'])+contributions['EUR']+contributions['USD']*(rate or ZERO)
        desired = {r['instrument_id']: nav*D(r['weight'])/100 for r in spec['rows']}
        exposure = {r['instrument_id']: D(r['value_eur']) for r in diagnosis['rows']}
        floor = desired[None]
        names = {i['id']:i['name'] for i in catalog['instruments']}
        listings = {l['id']:l for l in catalog['listings']}
        positions = {c['reference']: c for c in changed['components'] if c['kind']=='position'}
        rules = []
        seen = set()
        reasons = []
        for rule in body.rules:
            listing = listings.get(rule.listing_id)
            marks = market['prices'].get(rule.listing_id)
            if not listing or not marks or not marks['price']['value'] or (listing['currency']=='USD' and rate is None):
                reasons.append('Cotización sin identidad, vínculo de precio o FX válido: '+rule.listing_id)
                continue
            ident = listing['instrument_id']
            if ident in seen:
                raise ValueError('Elige una sola cotización operativa por instrumento para evitar repartir dos veces su déficit.')
            seen.add(ident)
            if ident not in desired:
                reasons.append('La cotización no tiene objetivo y límites globales: '+names[ident])
                continue
            rules.append((rule, listing, marks['price']))
            if marks['price']['status']=='provisional' or (listing['currency']=='USD' and fx['status']=='provisional'):
                result['provisional']=True
        for r in spec['rows']:
            if r['instrument_id'] and desired[r['instrument_id']] != exposure.get(r['instrument_id'], ZERO) and r['instrument_id'] not in seen:
                reasons.append('Falta configurar cotización, lote y costes de '+names[r['instrument_id']])
        if reasons:
            return dict(result, reasons=sorted(set(reasons)))
        fees_eur = ZERO

        def fee(gross, rule):
            return (D(rule.fixed_fee)+gross*D(rule.fee_bps)/10000).quantize(D('.01'),rounding=ROUND_UP)

        def trade(rule, listing, price, side):
            nonlocal fees_eur
            ident, currency = listing['instrument_id'], listing['currency']
            conversion, quote, step = rates[currency], D(price['value']), D(rule.quantity_step)
            delta = desired[ident]-exposure.get(ident,ZERO)
            if (side=='buy' and delta<=0) or (side=='sell' and delta>=0): return
            quantity = abs(delta)/conversion/quote
            old = positions.get(listing['id'])
            held = D(old['quantity']) if old else ZERO
            if side=='sell': quantity=min(quantity, held)
            else:
                total_cash = cash['EUR']+cash['USD']*(rate or ZERO)
                budget = min(cash[currency], spendable[currency], max(ZERO,total_cash-floor)/conversion)
                affordable = max(ZERO,budget-D(rule.fixed_fee))/(1+D(rule.fee_bps)/10000)/quote
                quantity=min(quantity,affordable)
            quantity=(quantity/step).to_integral_value(rounding=ROUND_DOWN)*step
            if side=='buy' and quantity>0:
                overspend=quantity*quote+fee(quantity*quote,rule)-budget
                if overspend>0:
                    steps=(overspend/(step*quote*(1+D(rule.fee_bps)/10000))).to_integral_value(rounding=ROUND_UP)
                    quantity=max(ZERO,quantity-steps*step)
            if quantity<=0: return
            gross=quantity*quote
            cost=fee(gross,rule)
            if side=='sell' and gross<=cost: return
            sign=D(1) if side=='buy' else D(-1)
            cash_delta=-sign*gross-cost
            if cash[currency]+cash_delta<0: raise ValueError('La simulación intentó gastar efectivo inexistente.')
            cash[currency]+=cash_delta
            spendable[currency]+=cash_delta
            fees_eur+=cost*conversion
            exposure[ident]=exposure.get(ident,ZERO)+sign*gross*conversion
            quantity_after=held+sign*quantity
            if old is None:
                old=dict(kind='position',reference=listing['id'],currency=currency,quantity='0',native_value='0',eur_value='0',
                         display_eur='0',status=price['status'],price=price,fx=fx if currency=='USD' else None,reasons=[])
                changed['components'].append(old)
                positions[listing['id']]=old
            old.update(quantity=text(quantity_after), native_value=text(quantity_after*quote), eur_value=text(quantity_after*quote*conversion))
            result['trades'].append(dict(instrument_id=ident,listing_id=listing['id'],label=names[ident],side=side,currency=currency,
                quantity=text(quantity),price=text(quote),gross_native=text(gross),fee_native=text(cost),gross_eur=text(gross*conversion),
                fee_eur=text(cost*conversion),price_mark=price,fx_mark=fx if currency=='USD' else None))

        if mode=='rebalance':
            for rule,listing,price in sorted(rules,key=lambda r:(r[0].priority,r[1]['instrument_id'])):
                trade(rule,listing,price,'sell')
        for rule,listing,price in sorted(rules,key=lambda r:(r[0].priority,-(desired[r[1]['instrument_id']]-exposure.get(r[1]['instrument_id'],ZERO)),r[1]['instrument_id'])):
            trade(rule,listing,price,'buy')
        changed['components']=[c for c in changed['components'] if c['kind']!='cash']
        for currency in cash:
            changed['components'].append(dict(kind='cash',reference=currency,currency=currency,native_value=text(cash[currency]),eur_value=text(cash[currency]*(rates[currency] or ZERO))))
            result['cash'].append(dict(currency=currency,initial=text(initial[currency]),contribution=text(contributions[currency]),final=text(cash[currency])))
        changed['exact_value']=text(nav-fees_eur)
        post=evaluate(changed,spec,catalog,corporate)
        for row in post['rows']:
            reasons += [row['label']+': '+r for r in row['reasons']]
        result.update(status='conflicts' if reasons or post['status']=='unavailable' else 'feasible', reasons=sorted(set(reasons)),
                      nav_after=text(nav-fees_eur),costs_eur=text(fees_eur),rows=post['rows'])
        return result

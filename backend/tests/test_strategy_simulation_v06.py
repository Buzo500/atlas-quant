"""Independent economics, failure atomicity and recovery of offline SMA runs."""
from copy import deepcopy
from decimal import Decimal as D, localcontext, ROUND_CEILING, ROUND_HALF_EVEN
from fractions import Fraction
import json

import pytest
from pydantic import ValidationError

from atlas_quant.book import balance
from atlas_quant.quality import digest
from atlas_quant.simulation_contracts import SimulationConfig
from atlas_quant.strategy_spec import OpeningObservation
from atlas_quant.strategy_simulation import SmaSimulation, restore_simulation, simulate
from test_strategy_evaluator_v06 import make_spec, observation


def config(**kw):
    return SimulationConfig(**dict(initial_cash_eur='1000', fixed_fee_eur='1', fee_bps='0', slippage_bps='0', **kw))


def opening(spec, i, price='10', **kw):
    time = spec.calendar.sessions[i].open_at
    payload = dict(spec_hash=spec.fingerprint, open_at=time, decision_at=time,
                   available_at=time if price is not None else None, price=price)
    payload.update(kw)
    return OpeningObservation(**payload)


def reference(spec):
    for i, close in enumerate(['10','10','10','12','10','8','8']):
        yield opening(spec, i, '10' if i != 6 else '8')
        yield observation(spec, i, close)


def ready(settings=None):
    spec = make_spec(fast=2, slow=3)
    sim = simulate(spec, settings or config(), [observation(spec, i, p) for i, p in enumerate(['10']*3+['12'])])
    return spec, sim


def test_manual_round_trip_cash_positions_costs_and_native_book_agree():
    spec = make_spec(fast=2, slow=3)
    sim = simulate(spec, config(), reference(spec))
    report = sim.report()
    fills = report['executions']
    assert [(x['side'], x['fill']['quantity'], x['fill']['fee_eur']) for x in fills] == [('buy','99','1.00'),('sell','99','1.00')]
    assert fills[0]['fill']['date'] == spec.calendar.sessions[4].date
    assert fills[1]['fill']['date'] == spec.calendar.sessions[6].date
    # 1,000 - 990 - 1 + 792 - 1 = 800; no position remains.
    assert report['final']['nav_eur'] == '800'
    assert report['final']['book']['positions'] == []
    assert report['final']['book']['balances'][0]['realized_pnl'] == '-200'
    assert balance(report['journal'], report['final']['book']['as_of_date'], multicurrency=True) == report['final']['book']
    assert report['strategy_state']['target_weight'] == 0


def test_gap_at_next_open_uses_open_not_signal_close():
    spec, sim = ready()
    row = sim.process(opening(spec, 4, '20'))
    assert row['executions'][0]['fill']['quantity'] == '49'
    assert row['executions'][0]['fill']['price_eur'] == '20'
    assert row['book']['balances'][0]['cash'] == '19.00'


@pytest.mark.parametrize('capital,step,price,fee,bps,weight', [
    ('100','1','9.93','1','7','1'), ('100','0.1','9.93','1','7','0.4'),
    ('0.01','1','0.014','0','0','1'), ('1','0.01','0.333','0','1','0.8'),
    ('100','3','9.93','1.99','19.77','0.7'), ('1','1','10','2','0','1'),
])
def test_lot_sizing_matches_exhaustive_fraction_oracle(capital, step, price, fee, bps, weight):
    settings = SimulationConfig(initial_cash_eur=capital, quantity_step=step, fixed_fee_eur=fee,
        fee_bps=bps, slippage_bps='0', strategy_weight=weight)
    spec, sim = ready(settings)
    row = sim.process(opening(spec, 4, price))
    affordable = []
    for lots in range(1, 1001):
        quantity = D(step)*lots
        gross = (quantity*D(price)).quantize(D('.01'), rounding=ROUND_HALF_EVEN)
        commission = (D(fee)+gross*D(bps)/10000).quantize(D('.01'), rounding=ROUND_CEILING)
        cash = D(capital)-gross-commission
        pos = Fraction(str(quantity))*Fraction(price)
        if gross > 0 and cash >= 0 and pos <= Fraction(weight)*(Fraction(str(cash))+pos):
            affordable.append(quantity)
    fill = row['executions'][0]['fill']
    assert (D(fill['quantity']) if fill else D(0)) == max(affordable, default=D(0))


def test_slippage_and_settlement_reconcile_nav_change_exactly():
    spec, sim = ready(SimulationConfig(initial_cash_eur='1000', quantity_step='0.3',
        fixed_fee_eur='1.12', fee_bps='7.3', slippage_bps='13.7'))
    row = sim.process(opening(spec, 4, '9.931234567891'))
    fill = row['executions'][0]['fill']
    assert D(fill['price_eur']) > D(fill['reference_price_eur'])
    loss = D(fill['fee_eur']) + D(fill['slippage_eur']) + D(fill['settlement_adjustment_eur'])
    assert D(row['nav_eur']) == D('1000')-loss
    assert D(fill['quantity']) % D('0.3') == 0


@pytest.mark.parametrize('changes,reason', [
    ({'purchases_enabled':False}, 'purchases_disabled'),
    ({'strategy_weight':'1', 'max_position_weight':'0.4'}, 'target_exceeds_position_limit'),
    ({'fixed_fee_eur':'1001'}, 'insufficient_budget_for_lot'),
    ({'quantity_step':'10000'}, 'insufficient_budget_for_lot'),
])
def test_rejection_does_not_fill_or_retry_but_preserves_logical_target(changes, reason):
    settings = SimulationConfig(**(config().model_dump() | changes))
    spec, sim = ready(settings)
    before = sim.report()['journal']
    row = sim.process(opening(spec, 4))
    assert row['executions'][0]['reason'] == reason
    assert sim.report()['journal'] == before
    assert sim.report()['strategy_state']['target_weight'] == 1
    assert sim.report()['pending_intent'] is None
    assert sim.process(opening(spec, 5))['executions'] == []


@pytest.mark.parametrize('kwargs,reason', [
    ({'price':None}, 'opening_price_missing'),
    ({'available_at':'2026-01-05T09:00:01Z'}, 'opening_price_late'),
    ({'decision_at':'2026-01-05T09:00:01Z'}, 'opening_opportunity_expired'),
])
def test_bad_opening_expires_and_cannot_fill_later(kwargs, reason):
    spec, sim = ready()
    row = sim.process(opening(spec, 4, **kwargs))
    assert row['executions'][0]['reason'] == reason
    assert len(sim.report()['journal']) == 1
    sim.process(opening(spec, 5))
    assert len(sim.report()['journal']) == 1


def test_skipped_open_expires_at_next_event():
    spec, sim = ready()
    row = sim.process(observation(spec, 4, '10'))
    assert row['executions'][0]['reason'] == 'opening_opportunity_expired'
    assert len(sim.report()['journal']) == 1


def test_close_arriving_after_next_open_cannot_create_a_backdated_fill():
    spec = make_spec(fast=2, slow=3)
    sim = simulate(spec, config(), [observation(spec,i,'10') for i in range(3)])
    sim.process(opening(spec, 4))
    row = sim.process(observation(spec, 3, '12', available_at='2026-01-05T09:01:00Z', decision_at='2026-01-05T09:02:00Z'))
    assert row['executions'][0]['reason'] == 'decision_not_before_next_open'
    assert len(sim.report()['journal']) == 1


def test_open_not_yet_available_waits_without_consuming_intention():
    spec, sim = ready()
    before = sim.checkpoint()
    assert sim.process(opening(spec,4,decision_at='2026-01-05T08:59:00Z'))['status'] == 'waiting'
    assert before == sim.checkpoint()
    assert sim.process(opening(spec,4))['executions'][0]['status'] == 'filled'


def test_sale_fee_cannot_overdraw_cash_or_create_short():
    settings = SimulationConfig(initial_cash_eur='100', fixed_fee_eur='20', fee_bps='0',slippage_bps='0')
    spec, sim = ready(settings)
    sim.process(opening(spec, 4, '10'))  # 8 units; zero cash.
    sim.process(observation(spec, 4, '10'))
    sim.process(observation(spec, 5, '8'))
    row = sim.process(opening(spec, 6, '1'))
    assert row['executions'][0]['reason'] == 'insufficient_cash_for_sale_fee'
    assert row['book']['positions'][0]['quantity'] == '8'
    assert row['book']['balances'][0]['cash'] == '0.00'
    assert sim.report()['strategy_state']['target_weight'] == 0


def test_duplicate_and_correction_preserve_atomic_book_and_checkpoint():
    spec, sim = ready()
    event = opening(spec,4)
    sim.process(event)
    checkpoint = sim.checkpoint()
    assert sim.process(event)['status'] == 'duplicate'
    assert checkpoint == sim.checkpoint()
    with pytest.raises(ValueError, match='corregida'):
        sim.process(opening(spec,4,'11'))
    assert checkpoint == sim.checkpoint()
    with pytest.raises(ValueError, match='retroceder'):
        sim.process(observation(spec,2,'10'))
    assert checkpoint == sim.checkpoint()
    with pytest.raises(ValueError, match='otra especificación'):
        sim.process(opening(make_spec(fast=3,slow=4),5))
    assert checkpoint == sim.checkpoint()


def test_checkpoint_incremental_equals_batch_including_every_book_record():
    spec = make_spec(fast=2, slow=3)
    settings = config()
    stream = list(reference(spec))
    batch = simulate(spec, settings, stream).report()
    incremental = SmaSimulation(spec,settings)
    for event in stream:
        incremental.process(event)
        incremental = restore_simulation(spec,settings,incremental.checkpoint())
    assert incremental.report() == batch


def test_checkpoint_rejects_corruption_cost_changes_and_unknown_events():
    spec, sim = ready()
    saved = json.loads(sim.checkpoint())
    saved['payload']['events'][0]['observation']['close'] = '101'
    with pytest.raises(ValueError,match='corrupto'):
        restore_simulation(spec,config(),json.dumps(saved))
    with pytest.raises(ValueError,match='costes'):
        restore_simulation(spec,SimulationConfig(initial_cash_eur='999'),sim.checkpoint())
    saved['payload']['events'][0]['kind'] = 'execute_code'
    saved['sha256'] = digest(saved['payload'])
    with pytest.raises(ValueError,match='desconocido'):
        restore_simulation(spec,config(),json.dumps(saved))


def test_future_prices_do_not_change_prefix_decisions_or_economics():
    spec = make_spec(fast=2,slow=3)
    events = list(reference(spec))
    baseline = simulate(spec,config(),events).report()
    changed = events[:-2] + [opening(spec,6,'999'),observation(spec,6,'777')]
    later = simulate(spec,config(),changed).report()
    assert baseline['records'][:-2] == later['records'][:-2]
    assert baseline['journal'][:2] == later['journal'][:2]


@pytest.mark.parametrize('status', ['missing','unverified','corporate_action'])
def test_missing_or_unverified_marks_never_invent_flat_nav(status):
    spec, sim = ready()
    sim.process(opening(spec,4))
    row = sim.process(observation(spec,4,status=status))
    assert row['nav_eur'] is None and row['risk'] == 'valuation_unavailable'
    assert row['book']['positions'][0]['quantity'] == '99'
    assert len(sim.report()['journal']) == 2
    if status == 'corporate_action':
        assert sim.process(opening(spec,5))['nav_eur'] is None


def test_exposure_drift_is_reported_without_an_unrequested_sale():
    spec, sim = ready(SimulationConfig(initial_cash_eur='1000', strategy_weight='0.4',
        max_position_weight='0.4', fixed_fee_eur='0', fee_bps='0',slippage_bps='0'))
    sim.process(opening(spec,4))
    row = sim.process(observation(spec,4,'20'))
    assert row['risk'] == 'position_limit_exceeded'
    assert len(sim.report()['journal']) == 2


def test_decimal_context_and_returned_document_mutation_do_not_change_results():
    spec = make_spec(fast=2,slow=3)
    with localcontext() as ctx:
        ctx.prec = 2
        low = simulate(spec, config(), reference(spec))
        report = low.report()
    with localcontext() as ctx:
        ctx.prec = 90
        high = simulate(spec, config(), reference(spec)).report()
    assert report == high
    saved = deepcopy(report)
    report['journal'][0]['event']['gross_amount'] = '0'
    assert low.report() == saved


@pytest.mark.parametrize('field,value', [
    ('initial_cash_eur','0'), ('initial_cash_eur',1000), ('initial_cash_eur','1e3'),
    ('initial_cash_eur','1.001'), ('quantity_step','0'), ('quantity_step','-1'),
    ('strategy_weight','1.01'), ('max_position_weight','2'), ('slippage_bps','1001'),
    ('fee_bps','NaN'), ('purchases_enabled',1), ('fixed_fee_eur','0.001'),
])
def test_config_rejects_ambiguous_or_unbounded_inputs(field,value):
    with pytest.raises(ValidationError):
        SimulationConfig(**(config().model_dump() | {field:value}))


def test_resource_limit_and_bad_calendar_are_atomic(monkeypatch):
    import atlas_quant.strategy_simulation as module
    spec, sim = ready()
    checkpoint = sim.checkpoint()
    monkeypatch.setattr(module,'MAX_EVENTS',4)
    with pytest.raises(ValueError,match='40.000'):
        sim.process(opening(spec,4))
    assert sim.checkpoint() == checkpoint
    monkeypatch.setattr(module,'MAX_CHECKPOINT_BYTES',10)
    with pytest.raises(ValueError,match='demasiado grande'):
        restore_simulation(spec,config(),checkpoint)


def test_late_close_does_not_backdate_book_or_replace_newer_open_mark():
    spec, sim = ready()
    sim.process(opening(spec,4,'10'))
    sim.process(opening(spec,5,'20'))
    row = sim.process(observation(spec,4,'11',available_at='2026-01-06T09:01:00Z',decision_at='2026-01-06T09:02:00Z'))
    assert row['book']['as_of_date'] == '2026-01-06'
    assert row['valuation_price_at'] == spec.calendar.sessions[5].open_at
    assert row['nav_eur'] == '1989'  # 99 * 20 + 9, not the obsolete close of 11.


def test_waiting_data_then_arrival_does_not_use_unavailable_close():
    spec, sim = ready()
    sim.process(opening(spec,4))
    row = sim.process(observation(spec,4,'1000',available_at='2026-01-05T17:03:00Z'))
    assert row['evaluation']['status'] == 'waiting'
    assert row['nav_eur'] is None
    row = sim.process(observation(spec,4,'1000',available_at='2026-01-05T17:03:00Z',decision_at='2026-01-05T17:04:00Z'))
    assert row['nav_eur'] == '99009'


def test_before_start_cannot_show_funded_book_in_the_past():
    spec = make_spec(fast=2,slow=3)
    sim = SmaSimulation(spec,config())
    before = sim.checkpoint()
    result = sim.process(observation(spec,0,decision_at='2025-12-31T17:00:00Z'))
    assert result['reason'] == 'simulation_not_started'
    assert before == sim.checkpoint()


def test_book_failure_does_not_consume_sell_or_mutate_economic_state():
    # The native book bounds monetary values at 1e18. A hypothetical huge
    # quote exceeds that bound; a staged failure must not sell or consume.
    settings = SimulationConfig(initial_cash_eur='1000000000000', fixed_fee_eur='0',fee_bps='0',slippage_bps='0')
    spec, sim = ready(settings)
    sim.process(opening(spec,4,'1'))
    sim.process(observation(spec,4,'10'))
    sim.process(observation(spec,5,'8'))
    before = sim.checkpoint()
    with pytest.raises(ValueError,match='1e18'):
        sim.process(opening(spec,6,'10000000'))
    assert before == sim.checkpoint()
    assert sim.report()['final']['book']['positions'][0]['quantity'] == '1000000000000'
    assert sim.process(opening(spec,6,'1'))['executions'][0]['status'] == 'filled'


def test_sell_adverse_rounding_and_costs_are_traceable():
    spec = make_spec(fast=2,slow=3)
    settings = SimulationConfig(initial_cash_eur='1000', fixed_fee_eur='1', fee_bps='5',slippage_bps='10')
    report = simulate(spec,settings,reference(spec)).report()
    sold = report['executions'][1]['fill']
    bought = report['executions'][0]['fill']
    assert D(sold['price_eur']) < D(sold['reference_price_eur'])
    quantity = D(bought['quantity'])
    market_loss = quantity*(D(sold['reference_price_eur'])-D(bought['reference_price_eur']))
    costs = sum((D(f[k]) for f in (bought,sold)
                 for k in ('fee_eur','slippage_eur','settlement_adjustment_eur')),D(0))
    assert D(report['final']['nav_eur']) == D('1000')+market_loss-costs


def test_reference_cli_and_reproduction_are_isolated(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    from run_sma_simulation import reproduce
    root = Path(__file__).resolve().parents[2]
    target = tmp_path/'economic.json'
    args = [sys.executable,str(root/'tools/run_sma_simulation.py')]
    completed = subprocess.run(args+['--output',str(target)],capture_output=True,text=True,check=True)
    result = json.loads(completed.stdout)
    assert result['fills'] == 2 and result['final_nav_eur'] == '818'
    document = target.read_text(encoding='utf-8')
    assert reproduce(document)['replay_incremental_parity'] is True
    completed = subprocess.run(args+['--reproduce',str(target)],capture_output=True,text=True,check=True)
    assert json.loads(completed.stdout)['reproduced'] is True
    failed = subprocess.run(args+['--output',str(target)],capture_output=True,text=True)
    assert failed.returncode == 1 and target.read_text(encoding='utf-8') == document
    saved = json.loads(document)
    saved['result']['final']['nav_eur'] = '999999'
    with pytest.raises(ValueError,match='huella'):
        reproduce(json.dumps(saved))

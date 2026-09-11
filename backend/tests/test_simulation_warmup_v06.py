"""Warm-up is indicator input, never account activity or a pending order."""
import json
import pytest
from atlas_quant.quality import digest
from atlas_quant.strategy_simulation import SmaSimulation, restore_simulation
from test_strategy_evaluator_v06 import make_spec, observation
from test_strategy_simulation_v06 import config, opening


def test_warmup_then_new_cross_matches_manual_round_trip_and_recovers():
    spec = make_spec(count=7, fast=2, slow=3)
    warmup = tuple(observation(spec, i, '10') for i in range(3))
    sim = SmaSimulation(spec, config(), warmup=warmup)
    report = sim.report()
    assert report['events'] == [] and report['executions'] == [] and report['pending_intent'] is None
    assert len(report['journal']) == 1
    assert report['final']['book']['as_of_date'] == spec.calendar.sessions[3].date
    assert report['final']['nav_eur'] == '1000'
    assert restore_simulation(spec, config(), sim.checkpoint()).report() == report
    for i, price in enumerate(['12', '10', '8', '8'], start=3):
        sim.process(opening(spec, i, '8' if i == 6 else '10'))
        sim.process(observation(spec, i, price))
        assert restore_simulation(spec, config(), sim.checkpoint()).report() == sim.report()
    # First cross day 4; buy 99 at 10 + 1 fee on day 5; sell at 8 - 1 on day 7.
    assert sim.report()['final']['nav_eur'] == '800'
    assert [(r['side'], r['fill']['quantity']) for r in sim.report()['executions']] == [('buy', '99'), ('sell', '99')]
    assert sim.report()['journal'][1]['date'] == spec.calendar.sessions[4].date


def test_already_above_at_boundary_does_not_buy_without_new_cross():
    spec = make_spec(count=6, fast=2, slow=3)
    sim = SmaSimulation(spec, config(), warmup=tuple(observation(spec, i, str(i+10)) for i in range(3)))
    for i in range(3, 6):
        sim.process(opening(spec, i))
        sim.process(observation(spec, i, str(i+10)))
    assert sim.report()['executions'] == []
    assert sim.report()['final']['nav_eur'] == '1000'


@pytest.mark.parametrize('case', ['non_prefix', 'future', 'too_long', 'untyped'])
def test_invalid_warmup_rejected(case):
    spec = make_spec(count=7, fast=2, slow=3)
    warmup = tuple(observation(spec, i) for i in range(3))
    if case == 'non_prefix': warmup = warmup[1:]
    if case == 'future': warmup = warmup[:-1] + (warmup[-1].model_copy(update=dict(decision_at=spec.calendar.sessions[3].open_at)),)
    if case == 'too_long': warmup += (observation(spec, 3),)
    if case == 'untyped': warmup = ({'close': '10'},)
    with pytest.raises(ValueError):
        SmaSimulation(spec, config(), warmup=warmup)


def test_no_replay_of_account_events_during_warmup_and_checkpoint_tamper():
    spec = make_spec(count=7, fast=2, slow=3)
    sim = SmaSimulation(spec, config(), warmup=tuple(observation(spec, i) for i in range(3)))
    before = sim.report()
    for event in (opening(spec, 0), observation(spec, 2)):
        with pytest.raises(ValueError, match='calentamiento'):
            sim.process(event)
        assert sim.report() == before
    envelope = json.loads(sim.checkpoint())
    envelope['payload']['warmup'][0]['close'] = '200'
    envelope['sha256'] = digest(envelope['payload'])
    with pytest.raises(ValueError, match='otra especificación'):
        restore_simulation(spec, config(), json.dumps(envelope))

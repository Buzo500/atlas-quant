"""Retrospective assumptions never become accredited inputs; exports replay offline."""
from datetime import date, timedelta
import hashlib
import json
import zipfile

import pytest
from pydantic import ValidationError

from atlas_quant.quality import digest
from atlas_quant.retrospective import (
    RetrospectiveRequest, RetrospectiveSpec, evaluate, freeze, prices_csv,
)
from atlas_quant.strategy_spec import FrozenCalendar, FrozenPriceSource, SmaSpec
from run_retrospective import bundle_files, export, run, verify_bundle, verify_report


def inputs():
    days = [(date(2025, 1, 1)+timedelta(days=i)).isoformat() for i in range(14)]
    rows = []
    for i, close in enumerate([10, 10, 10, 12, 10, 8, 8]*2):
        op = 8 if i in (6, 13) else 10
        rows.append(dict(date=days[i], open=str(op), high=str(max(op, close)), low=str(min(op, close)),
                         close=str(close), volume='100', dividends='0', splits='0'))
    document = prices_csv(rows)
    body = dict(symbol='TEST', instrument_id='TEST_ASSET', market='TEST', expected_dates=days,
        holdout_date=days[7], fast=2, slow=3, config=dict(initial_cash_eur='1000', fixed_fee_eur='1',
        fee_bps='0', slippage_bps='0'), provider='Fixture ficticio', calendar_source='Calendario ficticio',
        event_review='Sin eventos en el fixture ficticio', acknowledge_assumptions=True,
        source_sha256=hashlib.sha256(document.encode()).hexdigest())
    return body, document, rows


def frozen_inputs():
    body, document, _ = inputs()
    return freeze(RetrospectiveRequest.model_validate_json(json.dumps(body)), document)


def resign(frozen):
    frozen['frozen_hash'] = digest({k:v for k,v in frozen.items() if k != 'frozen_hash'})
    return frozen


def test_reference_arithmetic_and_holdout_absent():
    frozen = frozen_inputs()
    result = evaluate(frozen)
    assert [m['final_nav_eur'] for m in result['development']['metrics']] == ['800', '801', '1000']
    assert result['evidence_verified'] is False
    assert frozen['spec']['source']['basis_verified'] is False
    assert frozen['spec']['calendar']['verified'] is False
    assert result['holdout']['evaluated'] is False
    assert len(frozen['rows']) == 7
    assert all(r['date'] < '2025-01-08' for r in result['development']['curve'])


def test_accredited_contracts_reject_retrospective_models_and_json():
    spec = RetrospectiveSpec.model_validate_json(json.dumps(frozen_inputs()['spec']))
    for model, value in [(SmaSpec, spec), (FrozenPriceSource, spec.source), (FrozenCalendar, spec.calendar)]:
        with pytest.raises(ValidationError):
            model.model_validate(value)
        with pytest.raises(ValidationError):
            model.model_validate_json(value.model_dump_json())


@pytest.mark.parametrize('field,value', [('acknowledge_assumptions',False),('acknowledge_assumptions',1),
    ('currency','USD'),('fast',3),('holdout_date','2030-01-01')])
def test_request_rejects_invalid_assumptions(field, value):
    body, _, _ = inputs()
    body[field] = value
    with pytest.raises(ValueError):
        RetrospectiveRequest.model_validate_json(json.dumps(body))


@pytest.mark.parametrize('problem', ['gap', 'duplicate', 'unsorted', 'outside', 'negative', 'nan',
                                    'high', 'zero_volume', 'split', 'dividend', 'precision'])
def test_csv_rejects_inconsistent_observed_inputs(problem):
    body, _, rows = inputs()
    if problem == 'gap': rows.pop(2)
    elif problem == 'duplicate': rows[1] = dict(rows[0])
    elif problem == 'unsorted': rows[0], rows[1] = rows[1], rows[0]
    elif problem == 'outside': rows[-1]['date'] = '2030-01-01'
    else:
        key,value={'negative':('close','-1'), 'nan':('open','NaN'), 'high':('high','1'),
            'zero_volume':('volume','0'), 'split':('splits','2'), 'dividend':('dividends','1'),
            'precision':('close','10.0000000000001')}[problem]
        rows[0][key] = value
    document = prices_csv(rows)
    body['source_sha256'] = hashlib.sha256(document.encode()).hexdigest()
    with pytest.raises(ValueError):
        freeze(RetrospectiveRequest.model_validate_json(json.dumps(body)), document)


def test_changed_reserved_prices_do_not_change_development_values_or_expose_them():
    a = evaluate(frozen_inputs())['development']
    body, _, rows = inputs()
    for row in rows[7:]:
        row.update(open='999', high='999', low='999', close='999')
    document = prices_csv(rows)
    body['source_sha256'] = hashlib.sha256(document.encode()).hexdigest()
    frozen = freeze(RetrospectiveRequest.model_validate_json(json.dumps(body)), document)
    b = evaluate(frozen)['development']
    assert {k:v for k,v in a.items() if k != 'report_hash'} == {k:v for k,v in b.items() if k != 'report_hash'}
    assert '999' not in prices_csv(frozen['rows'])


@pytest.mark.parametrize('problem', ['clock', 'verified', 'identity', 'reserved_price', 'opened', 'unknown',
    'holdout_values', 'holdout_hash', 'holdout_count', 'numeric_false_source', 'numeric_false_calendar'])
def test_frozen_rejects_rehashed_changes_to_fixed_policy(problem):
    frozen = frozen_inputs()
    if problem == 'clock': frozen['close_availability']['2025-01-01'] = '2025-01-01T17:00:00Z'
    elif problem == 'verified': frozen['spec']['source']['basis_verified'] = True
    elif problem == 'identity': frozen['spec']['source']['listing_id'] = 'OTHER'
    elif problem == 'reserved_price': frozen['rows'].append(dict(frozen['rows'][0], date='2025-01-08'))
    elif problem == 'opened': frozen['holdout']['evaluated'] = True
    elif problem == 'holdout_values': frozen['holdout']['prices'] = [999]
    elif problem == 'holdout_hash': frozen['holdout']['rows_hash'] = 'z'*64
    elif problem == 'holdout_count': frozen['holdout']['sessions'] = 7.0
    elif problem == 'numeric_false_source': frozen['spec']['source']['basis_verified'] = 0
    elif problem == 'numeric_false_calendar': frozen['spec']['calendar']['verified'] = 0
    else: frozen['unexpected'] = 'value'
    with pytest.raises(ValueError):
        evaluate(resign(frozen))


def test_source_hash_checked_before_freeze():
    body, document, _ = inputs()
    with pytest.raises(ValueError, match='huella'):
        freeze(RetrospectiveRequest.model_validate_json(json.dumps(body)), document+'\n')


def test_bundle_reproduces_and_is_deterministic_without_overwrite(tmp_path):
    report = run(frozen_inputs())
    a,b=tmp_path/'a.zip',tmp_path/'b.zip'
    export(report,a); export(report,b)
    assert a.read_bytes() == b.read_bytes()
    assert verify_bundle(a) == report
    with pytest.raises(FileExistsError): export(report,a)
    with zipfile.ZipFile(a) as archive:
        for name in ('prices.csv','nav.csv','trades.csv'):
            assert b'2025-01-08' not in archive.read(name)


@pytest.mark.parametrize('problem', ['price_csv', 'report', 'code', 'traversal', 'duplicate'])
def test_bundle_rejects_corruption_and_unexpected_members(tmp_path, problem):
    report = run(frozen_inputs())
    files = bundle_files(report)
    if problem == 'price_csv': files['prices.csv'] += b'corrupt'
    if problem == 'report':
        report['result']['development']['metrics'][0]['final_nav_eur'] = '2000'
        files['report.json'] = json.dumps(report).encode()
    if problem == 'code':
        report['code_sha256'] = {}
        files['report.json'] = json.dumps(report).encode()
    if problem == 'traversal': files['../unexpected.txt'] = b'unsafe'
    path = tmp_path/'bad.zip'
    with zipfile.ZipFile(path,'w') as archive:
        for name,data in files.items(): archive.writestr(name,data)
        if problem == 'duplicate':
            with pytest.warns(UserWarning): archive.writestr('report.json',files['report.json'])
    with pytest.raises(ValueError): verify_bundle(path)
    assert not (tmp_path.parent/'unexpected.txt').exists()


@pytest.mark.parametrize('value', [None, [], 'unexpected'])
def test_untrusted_json_root_rejected(value):
    with pytest.raises(ValueError): evaluate(value)
    with pytest.raises(ValueError): verify_report(value)

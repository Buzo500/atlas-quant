from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from atlas_quant.app import create_app
from atlas_quant.candidate_contracts import CandidateComparisonInput, CandidateComparison
from atlas_quant.candidate_service import CandidateService
from atlas_quant.catalog import IdentityNotFound, RevisionConflict
from atlas_quant.lab_preflight import inspect_source, SourcePreflight
from test_lab_v06 import lab, LOCAL, open_request  # noqa: F401
from test_candidates_v06 import request, revision


def records(store):
    return store.read(lambda w: list(w.db.execute('SELECT * FROM records ORDER BY kind,id')))


def test_source_preflight_is_readonly_and_never_certifies_or_exposes_results(lab):
    store, service, body = lab
    prior = records(store)
    value = store.read(lambda w: inspect_source(*service._snapshot(w, body)))
    SourcePreflight.model_validate(value)
    assert value['rows'] == 14
    assert {c['code'] for c in value['checks'] if c['status'] == 'review'} == {'events', 'protocol'}
    assert 'bars' not in value and 'holdout' not in value and 'metrics' not in value
    assert records(store) == prior


def test_source_preflight_lists_independent_defects_and_context_changes(lab):
    store, service, body = lab
    source, listing, corp = store.read(lambda w: service._snapshot(w, body))
    original = inspect_source(source, listing, corp)
    source['quality_evidence'][source['symbol']]['basis_verified'] = False
    source['bars'].pop(2)
    source['bars'][0]['available_at'] = None
    source['bars'][1]['available_at'] = source['bars'][1]['date'] + 'T01:00:00Z'
    value = inspect_source(source, listing, corp)
    checks = {c['code']: c for c in value['checks']}
    assert checks['basis_calendar']['status'] == 'block'
    assert checks['coverage']['message'].startswith('1 sesiones')
    assert checks['availability']['message'].startswith('1 cierres sin disponibilidad y 1 anteriores')
    assert value['context_hash'] != original['context_hash']


def test_historical_search_is_literal_unicode_paged_and_revision_specific(lab):
    store, _, _ = lab
    s = CandidateService(store)
    one = s.create(request(status='discarded', reason='PÉRDIDA del 50%_literal; descartar.'))
    s.revise(one['candidate_id'], revision(one, status='watchlist'))
    s.create(request(name='Otra hipótesis', reason='Ninguna pérdida observada todavía.'))
    before = records(store)
    assert s.search('pérdida', 'discarded')['items'] == [one]
    assert s.search('50%_')['items'] == [one]
    assert s.search("' OR 1=1 --")['items'] == []
    assert s.search('pérdida', 'watchlist')['items'] == []
    assert len(s.search(limit=1, offset=1)['items']) == 1
    assert records(store) == before


def refs(*values):
    return CandidateComparisonInput(items=[dict(candidate_id=v['candidate_id'], revision=v['revision']) for v in values])


def test_comparison_preserves_captured_holdout_and_is_readonly(lab):
    store, lab_service, body = lab
    p = lab_service.create(body)
    s = CandidateService(store)
    one = s.create(request(protocol_ids=[p['protocol']['id']]))
    lab_service.open_holdout(p['protocol']['id'], open_request(p['protocol']['id']))
    two = s.revise(one['candidate_id'], revision(one, status='discarded'))
    before = records(store)
    value = s.compare(refs(one, two))
    CandidateComparison.model_validate(value)
    assert value['same_context']
    assert value['items'][0]['evidence'][0]['holdout_hash'] is None
    assert value['items'][1]['evidence'][0]['holdout_hash'] is not None
    assert s.compare(refs(one, two)) == value
    assert records(store) == before


def test_comparison_marks_missing_evidence_and_changed_costs(lab):
    store, lab_service, body = lab
    s = CandidateService(store)
    empty = s.create(request())
    p = lab_service.create(body)
    one = s.create(request(name='Con evidencia', protocol_ids=[p['protocol']['id']]))
    assert not s.compare(refs(empty, one))['same_context']
    changed = lab_service.create(body.model_copy(update=dict(config=body.config.model_copy(update=dict(fixed_fee_eur='2')))))
    two = s.create(request(name='Con otros costes', protocol_ids=[changed['protocol']['id']]))
    assert not s.compare(refs(one, two))['same_context']
    assert len({v['context_hash'] for v in s.compare(refs(one, two))['contexts']}) == 2


def test_missing_or_tampered_comparison_fails_atomically(lab):
    store, lab_service, body = lab
    s = CandidateService(store)
    p = lab_service.create(body)
    one = s.create(request(protocol_ids=[p['protocol']['id']]))
    two = s.create(request(name='Otra candidata'))
    bad = refs(one, two).model_copy(deep=True)
    bad.items[1].revision = 100
    with pytest.raises(IdentityNotFound): s.compare(bad)
    def corrupt(w):
        value = deepcopy(w.get('lab_protocol', p['protocol']['id']))
        value['development']['report_hash'] = 'alterado'
        w.put('lab_protocol', value | dict(id=p['protocol']['id']))
    store.atomic(corrupt)
    with pytest.raises(RevisionConflict): s.compare(refs(one, two))


@pytest.mark.parametrize('items', [[], [dict(candidate_id='a'*64, revision=1)]*2,
    [dict(candidate_id=chr(97+n)*64, revision=1) for n in range(5)]])
def test_comparison_bounds(items):
    with pytest.raises(ValidationError): CandidateComparisonInput(items=items)


def test_discovery_http_contracts_and_local_guard(lab):
    store, _, body = lab
    s = CandidateService(store)
    one = s.create(request())
    two = s.create(request(name='Otra candidata'))
    with TestClient(create_app(store.path.parent, run_worker=False)) as c:
        response = c.get('/api/lab/sources/preflight', params=dict(series_id=body.series_id, series_version=body.series_version))
        assert response.status_code == 200
        assert c.get('/api/lab/candidates/search', params=dict(q='Hipótesis')).status_code == 200
        assert c.get('/api/lab/candidates/search', params=dict(q='x'*201)).status_code == 422
        assert c.get('/api/lab/candidates/search', params=dict(status='approved')).status_code == 422
        url = '/api/lab/candidates/compare'
        payload = refs(one, two).model_dump(mode='json')
        assert c.post(url, json=payload).status_code == 403
        assert c.post(url, json=payload, headers=LOCAL).status_code == 200

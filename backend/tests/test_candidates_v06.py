"""Research decisions cannot rewrite historical evidence or authorize execution."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from atlas_quant.app import create_app
from atlas_quant.candidate_contracts import CandidateInput, CandidateRevisionInput, CandidateRevision
from atlas_quant.candidate_service import CandidateService
from atlas_quant.catalog import IdentityNotFound, RevisionConflict
from atlas_quant.store import UnitOfWork, Store
from test_lab_v06 import lab, LOCAL, open_request  # noqa: F401


def request(**changes):
    return CandidateInput(**(dict(name='Hipótesis SMA', hypothesis='El cruce SMA puede filtrar tendencias.', reason='Primera hipótesis, aún sin evaluar.') | changes))


def revision(value, **changes):
    return CandidateRevisionInput(**(dict(name=value['name'], hypothesis=value['hypothesis'], reason='Revisión explícita de la evidencia disponible.',
        status=value['status'], protocol_ids=value['protocol_ids'], expected_revision=value['revision']) | changes))


def test_revision_history_preserves_discard_reasons_and_evidence(lab):
    store, lab_service, body = lab
    before = store.read(lambda w: (w.portfolio_list(),w.catalog()))
    service = CandidateService(store)
    first = service.create(request())
    CandidateRevision.model_validate(first)
    ident = first['candidate_id']
    assert first['revision'] == 1 and first['evidence'] == []
    protocol = lab_service.create(body)
    second = service.revise(ident, revision(first, protocol_ids=[protocol['protocol']['id']], status='watchlist'))
    assert second['evidence'][0]['holdout_hash'] is None
    lab_service.open_holdout(protocol['protocol']['id'], open_request(protocol['protocol']['id']))
    assert service.read(ident) == second  # Opening a result cannot update a candidate.
    third = service.revise(ident, revision(second, status='discarded', reason='Resultados desfavorables en la prueba final.'))
    assert third['evidence'][0]['holdout_hash'] is not None
    assert service.revisions(ident)['items'] == [third,second,first]
    assert service.revisions(ident,offset=1,limit=1)['items'] == [second]
    assert CandidateService(Store(store.path)).read(ident) == third
    assert service.create(request()) == first
    assert store.read(lambda w: (w.portfolio_list(),w.catalog())) == before
    assert service.history()['items'][0]['status'] == 'discarded'


def test_conflicting_revisions_never_merge_silently(lab):
    store, _, _ = lab
    service = CandidateService(store)
    first = service.create(request())
    with ThreadPoolExecutor(2) as pool:
        futures = [pool.submit(service.revise, first['candidate_id'], revision(first, reason=f'Decisión concurrente número {n}.')) for n in range(2)]
        outcomes=[]
        for future in futures:
            try: outcomes.append(future.result())
            except RevisionConflict: outcomes.append(None)
    assert sum(v is not None for v in outcomes) == 1
    assert len(service.revisions(first['candidate_id'])['items']) == 2
    assert store.read(lambda w: w.db.execute("SELECT COUNT(*) FROM audit WHERE event='candidate.revised'").fetchone()[0]) == 1


def test_cannot_remove_report_or_attach_missing_report(lab):
    store, lab_service, body = lab
    service = CandidateService(store)
    protocol = lab_service.create(body)['protocol']['id']
    first = service.create(request(protocol_ids=[protocol]))
    with pytest.raises(ValueError, match='eliminar evidencia'):
        service.revise(first['candidate_id'], revision(first,protocol_ids=[]))
    with pytest.raises(IdentityNotFound):
        service.revise(first['candidate_id'], revision(first,protocol_ids=[protocol,'a'*64]))
    assert service.read(first['candidate_id']) == first


def test_audit_failure_rolls_back_revision_and_current_pointer(lab, monkeypatch):
    store, _, _ = lab
    service = CandidateService(store)
    first = service.create(request())
    original = UnitOfWork.audit
    def fail(work, event, *args, **kwargs):
        if event.startswith('candidate.'): raise RuntimeError('audit unavailable')
        return original(work,event,*args,**kwargs)
    monkeypatch.setattr(UnitOfWork,'audit',fail)
    with pytest.raises(RuntimeError): service.revise(first['candidate_id'],revision(first))
    with pytest.raises(RuntimeError): service.create(request(name='Otra hipótesis'))
    assert service.read(first['candidate_id']) == first
    assert len(service.history()['items']) == 1
    assert len(service.revisions(first['candidate_id'])['items']) == 1


@pytest.mark.parametrize('changes', [dict(status='approved'),dict(hypothesis=''),dict(reason=''),dict(protocol_ids=['a'*64]*2),dict(send_orders=True)])
def test_strict_research_contract(changes):
    with pytest.raises(ValueError): request(**changes)


def test_http_requires_local_guard_and_matching_revision(lab):
    store, _, _ = lab
    with TestClient(create_app(store.path.parent,run_worker=False)) as client:
        body=request().model_dump(mode='json')
        assert client.post('/api/lab/candidates',json=body).status_code == 403
        response=client.post('/api/lab/candidates',json=body,headers=LOCAL)
        assert response.status_code == 200, response.text
        first=response.json(); ident=first['candidate_id']
        assert client.get(f'/api/lab/candidates/{ident}').json() == first
        change=revision(first,status='discarded').model_dump(mode='json')
        assert client.post(f'/api/lab/candidates/{ident}/revisions',json=change,headers=LOCAL).status_code == 200
        assert client.post(f'/api/lab/candidates/{ident}/revisions',json=change,headers=LOCAL).status_code == 409
        assert len(client.get(f'/api/lab/candidates/{ident}/revisions').json()['items']) == 2
        assert client.get('/api/lab/candidates?limit=51').status_code == 422

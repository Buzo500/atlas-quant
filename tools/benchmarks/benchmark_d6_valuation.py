"""D6 representative load and recovery on a newly created disposable database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import gc
import json
from pathlib import Path
import sys
import time
import tracemalloc
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from atlas_quant.book import POLICY, MOVEMENT_COLUMNS
from atlas_quant.book_service import BookService
from atlas_quant.book_contracts import ImportInput
from atlas_quant.catalog import CatalogService
from atlas_quant.controls import update_settings, control_experiment
from atlas_quant.market_service import MarketService, PRICE_COLUMNS, FX_COLUMNS
from atlas_quant.market_contracts import MarketImport, FxBindingInput
from atlas_quant.quality import EvidenceInput
from atlas_quant.portfolios import PortfolioService
from atlas_quant.store import Store
from atlas_quant.valuation_service import ValuationService
from atlas_quant.valuation_contracts import ValuationInput, ValuationCut
from atlas_quant.backup import create_backup, restore_backup
from atlas_quant.worker_lock import WorkerLock


def sheet(columns, rows):
    return ','.join(columns)+'\n'+''.join(','.join(str(row.get(c,'')) for c in columns)+'\n' for row in rows)


def confirm(call, body):
    preview=call(body)
    return call(body.model_copy(update={'commit':True,'preview_token':preview['preview_token']}))


def seed(directory):
    store=Store(directory/'atlas.sqlite3')
    catalog=CatalogService(store)
    portfolio=PortfolioService(store).create('Carga sintética D6',POLICY)
    start=date(1990,1,1)
    days=[(start+timedelta(days=i)).isoformat() for i in range(10_000)]
    calendar='date,status,close_at\n'+''.join(f'{d},open,{d}T20:00:00Z\n' for d in days)
    evidence=EvidenceInput(symbol='ASSET',calendar_name='Calendario sintético',market='TEST',calendar_source='Fixture de carga explícito',calendar_verified=True,
        calendar_csv=calendar,price_basis='raw',basis_verified=True,basis_source='Cierres brutos ficticios')
    market=MarketService(store)
    bindings,mapping=[],{}
    for i in range(10):
        c=catalog.read()
        c=catalog.add('instrument',dict(expected_revision=c['revision'],name='Fixture '+str(i),source='Benchmark sintético'))
        instrument=next(item for item in c['instruments'] if item['name']=='Fixture '+str(i))
        c=catalog.add('listing',dict(expected_revision=c['revision'],instrument_id=instrument['id'],currency='USD'))
        listing=next(l for l in c['listings'] if l['instrument_id']==instrument['id'])
        mapping['S'+str(i)]=listing['id']
        request=MarketImport(name='Serie '+str(i),source='Benchmark sintético',listing_id=listing['id'],evidence=evidence,
            csv=sheet(PRICE_COLUMNS,[dict(date=d,listing_ref='ASSET',open='10',high='10',low='10',close='10',volume='1',currency='USD',available_at=d+'T20:01:00Z') for d in days]))
        s=confirm(lambda body:market.import_series('prices',body),request)['series']
        bindings.append(dict(listing_id=listing['id'],dataset_id=s['id'],dataset_version=s['version'],symbol='ASSET'))
    fx=confirm(lambda body:market.import_series('fx',body),MarketImport(name='FX',source='Benchmark sintético',evidence=evidence,
        csv=sheet(FX_COLUMNS,[dict(date=d,from_currency='USD',to_currency='EUR',rate='0.9',available_at=d+'T20:01:00Z') for d in days])))['series']
    service=PortfolioService(store)
    reviewed=service.bind(portfolio['id'],bindings)
    service.bind(portfolio['id'],bindings,True,reviewed['preview_token'])
    common=dict(currency='USD',fee_amount='0.00',fee_currency='USD',tax_amount='0.00',tax_currency='USD')
    movements=[dict(common,external_id='deposit',date=days[0],day_sequence=1,kind='deposit',gross_amount='100000.00')]
    movements += [dict(common,external_id='buy'+str(i),date=days[0],day_sequence=i+2,kind='buy',listing_ref='S'+str(i),quantity='1',unit_price='10',gross_amount='10.00') for i in range(10)]
    movements += [dict(common,external_id='fee'+str(i),date=days[1+i],day_sequence=1,kind='fee',gross_amount='0.01') for i in range(9989)]
    book=BookService(store,multicurrency=True)
    p=service.list()[0]
    confirm(lambda body:book.import_movements(p['id'],body),ImportInput(format_id='atlas-ledger-v2',expected_revision=p['revision'],source='Benchmark sintético',source_account='DEMO',as_of_date=days[-1],mapping=mapping,csv=sheet(MOVEMENT_COLUMNS,movements)))
    p=service.list()[0]
    confirm(lambda body:market.bind_fx(p['id'],body),FxBindingInput(expected_revision=p['revision'],series_id=fx['id'],series_version=fx['version']))
    p=service.list()[0]
    return store,p,days[-1]


def main():
    directory=ROOT/'var/validation'/('d6-benchmark-'+uuid4().hex)
    directory.mkdir(parents=True,exist_ok=False)
    store,p,day=seed(directory)
    service=ValuationService(store)
    request=ValuationInput(as_of_date=day,expected_revision=p['revision'])
    def calculate():
        start=time.perf_counter()
        result=service.calculate(p['id'],request)
        serialized=ValuationCut.model_validate(result['cut']).model_dump_json()
        assert result['cut']['status']=='complete' and result['cut']['value']=='89910.10'
        return time.perf_counter()-start,len(serialized)
    calculate()
    timings=[calculate()[0] for _ in range(5)]
    gc.collect()
    tracemalloc.start()
    calculate()
    _,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    for i in range(10):
        store.put('experiment',dict(id='control-'+str(i),status='running',provider='none',spent_usd=0,reserved_usd=0))
    control_store=Store(store.path)
    controls=[]
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(lambda:[calculate() for _ in range(3)])
        for i in range(20):
            start=time.perf_counter()
            if i%2:
                control_experiment(control_store,'control-'+str(i//2),'pause')
            else:
                update_settings(control_store,{'kill_switch':True})
            controls.append(time.perf_counter()-start)
            time.sleep(.03)
        future.result()
    saved=confirm(lambda body:service.calculate(p['id'],body),request)['cut']
    snapshot=create_backup(store.path,directory/'backups')
    target=directory/'restored.sqlite3'
    restore_backup(snapshot,target,directory/'before',instance_lock=WorkerLock(directory/'restore.lock'))
    recovered=ValuationService(Store(target)).read(p['id'],saved['id'])
    assert recovered==saved
    report=dict(directory=str(directory),bars=100_000,fx_observations=10_000,movements=10_000,listings=10,
        calculation_and_serialization_seconds=timings,python_peak_mib=peak/1024**2,
        control_boundary='application services, separate Store during valuation',controls_seconds=controls,
        control_p95_seconds=sorted(controls)[18],recovery_exact=True)
    report['passed']=max(timings)<=5 and peak<=256*1024**2 and report['control_p95_seconds']<1
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())

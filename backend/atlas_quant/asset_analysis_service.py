"""Coherent analytical snapshots and compare-and-save publication."""
import hmac
from . import asset_analysis
from .catalog import IdentityNotFound, RevisionConflict
from .computation import bounded_calculation
from .portfolios import fingerprint
from .targets_service import utc


def descriptor(ref, data, catalog):
    listing = next((l for l in catalog['listings'] if
        (ref['kind']=='native' and l['id']==data.get('listing_id')) or
        (ref['kind']=='legacy' and l.get('legacy_dataset_id')==ref['id'] and l.get('legacy_symbol')==ref['symbol'])),None)
    if listing is None:
        raise IdentityNotFound('La fuente no tiene una identidad explícita en el catálogo.')
    instrument=next(i for i in catalog['instruments'] if i['id']==listing['instrument_id'])
    return dict(key=fingerprint(ref),ref=ref,name=instrument['name'],dataset_name=data['name'],source=data['source'],
        instrument_id=instrument['id'],instrument_type=instrument['instrument_type'],listing_id=listing['id'],market=listing.get('market'),
        currency=listing['currency'],sha256=data.get('sha256') or data.get('manifest',{}).get('sha256'),
        date_min=data.get('date_min') or data['bars'][0]['date'],date_max=data.get('date_max') or data['bars'][-1]['date'],
        row_count=data.get('row_count') or len(data['bars']))


class AssetAnalysisService:
    def __init__(self, store):
        self.store=store

    def catalog(self):
        def read(work):
            catalog=work.catalog()
            sources=[]
            for data in work.analysis_price_metadata():
                native=data['kind']=='native_price'
                symbols=[data['symbol']] if native else sorted({l['legacy_symbol'] for l in catalog['listings'] if l.get('legacy_dataset_id')==data['id']})
                for symbol in symbols:
                    refs=dict(kind='native' if native else 'legacy',id=data['id'],version=data['version'],symbol=symbol)
                    sources.append(descriptor(refs,data,catalog))
            return dict(sources=sources,fx=work.analysis_fx_metadata(),limit=500)
        return self.store.read(read)

    @staticmethod
    def signature(work, body):
        return fingerprint(work.asset_analysis_stamp(body['sources'],body['fx']))

    @bounded_calculation
    def calculate(self, body):
        inputs=body.model_dump(exclude={'commit','preview_token'})
        def snapshot(work):
            keys=sorted({(r.id,r.version) for r in body.sources})
            sizes=[work.analysis_version_size(*key) for key in keys]
            if any(n is None for n in sizes):
                raise IdentityNotFound('Versión de precios no encontrada.')
            if sum(sizes)>200_000:
                raise ValueError('Máximo 200.000 barras de origen entre las fuentes elegidas.')
            catalog=work.catalog()
            datasets={key:work.dataset_version(*key) for key in keys}
            sources=[]
            for ref in body.sources:
                data=datasets[(ref.id,ref.version)]
                is_native=data.get('format_id')=='atlas-prices-v2'
                if is_native != (ref.kind=='native') or (is_native and data['symbol']!=ref.symbol) or not any(b['symbol']==ref.symbol for b in data['bars']):
                    raise ValueError('Identidad, símbolo o tipo de fuente incompatible.')
                sources.append((descriptor(ref.model_dump(),data,catalog),data))
            needs_fx=any(s['currency']=='USD' for s,_ in sources)
            if body.fx and not needs_fx:
                raise ValueError('Una comparación solo EUR no necesita una fuente FX.')
            fx=work.market_version('fx',body.fx.id,body.fx.version) if body.fx else None
            if body.fx and fx is None:
                raise IdentityNotFound('Versión FX no encontrada.')
            fx_source=dict(ref=body.fx.model_dump(),name=fx['name'],source=fx['source'],sha256=fx['sha256'],
                           date_min=fx['bars'][0]['date'],date_max=fx['bars'][-1]['date']) if fx else None
            return sources,fx,fx_source,work.corporate_state(),work.asset_analysis_stamp(inputs['sources'],inputs['fx'])
        sources,fx,fx_source,corporate,stamp=self.store.read(snapshot)
        signature=fingerprint(stamp)
        result=asset_analysis.calculate(sources,fx,fx_source,corporate,body)
        token=fingerprint(dict(policy=asset_analysis.POLICY,context=signature,inputs=inputs))
        value=dict(id=token,created_at=utc(),policy=asset_analysis.POLICY,context_hash=signature,
                   catalog_revision=stamp['catalog_revision'],corporate_revision=stamp['corporate_revision'],
                   inputs=dict(inputs,commit=False,preview_token=None),result=result,current=True,saved=body.commit)
        def publish(work):
            if self.signature(work,inputs)!=signature:
                raise RevisionConflict('Las fuentes o su contexto han cambiado. Revisa el análisis de nuevo.')
            if body.commit:
                if not body.preview_token or not hmac.compare_digest(token,body.preview_token):
                    raise RevisionConflict('Previsualización ausente u obsoleta.')
                old=work.get('asset_analysis',token)
                if old:
                    return old
                work.save_asset_analysis(value)
                work.audit('asset_analysis.saved',token,dict(context_hash=signature,sources=inputs['sources']))
            return value
        return dict(report=self.store.atomic(publish),preview_token=token,committed=body.commit)

    def report(self, ident):
        def read(work):
            value=work.get('asset_analysis',ident)
            if value is None:
                raise IdentityNotFound('Comparación guardada no encontrada.')
            return dict(value,current=value['context_hash']==self.signature(work,value['inputs']))
        return self.store.read(read)

    def history(self,offset=0,limit=20):
        return dict(reports=self.store.read(lambda w:w.asset_analysis_history(offset,limit)),offset=offset,limit=limit)

"""Metadata reads and immutable asset reports, independent of portfolio books."""
import json


class AssetAnalysisWork:
    def analysis_price_metadata(self, limit=500):
        rows = self.db.execute("""SELECT kind,id,json_extract(body,'$.name'),json_extract(body,'$.source'),
            json_extract(body,'$.version'),json_extract(body,'$.listing_id'),json_extract(body,'$.symbol'),
            COALESCE(json_extract(body,'$.sha256'),json_extract(body,'$.manifest.sha256')),
            json_extract(body,'$.bars[0].date'),json_extract(body,'$.bars[#-1].date'),json_array_length(body,'$.bars')
            FROM records WHERE kind IN ('dataset','native_price') ORDER BY rowid DESC LIMIT ?""",(limit,))
        names=('kind','id','name','source','version','listing_id','symbol','sha256','date_min','date_max','row_count')
        return [dict(zip(names,row)) for row in rows]

    def analysis_fx_metadata(self, limit=500):
        rows=self.db.execute("""SELECT id,json_extract(body,'$.version'),json_extract(body,'$.name'),json_extract(body,'$.source'),
            json_extract(body,'$.sha256'),json_extract(body,'$.bars[0].date'),json_extract(body,'$.bars[#-1].date')
            FROM fx_series ORDER BY rowid DESC LIMIT ?""",(limit,))
        return [dict(ref=dict(id=r[0],version=r[1]),name=r[2],source=r[3],sha256=r[4],date_min=r[5],date_max=r[6]) for r in rows]

    def analysis_version_size(self, ident, version):
        row=self.db.execute('SELECT json_array_length(body,\'$.bars\') FROM versions WHERE dataset_id=? AND version=?',(ident,version)).fetchone()
        return row[0] if row else None

    def asset_analysis_stamp(self, refs, fx):
        return dict(catalog_revision=self.db.execute('SELECT COALESCE(MAX(revision),0) FROM catalog_revisions').fetchone()[0],
            corporate_revision=self.db.execute('SELECT (SELECT COUNT(*) FROM corporate_versions)+(SELECT COUNT(*) FROM corporate_sources)').fetchone()[0],
            price_heads=[[r['kind'],r['id'],self.market_head('prices',r['id'])] for r in refs],
            fx_head=self.market_head('fx',fx['id']) if fx else None)

    def save_asset_analysis(self, value):
        summary=dict(id=value['id'],created_at=value['created_at'],start_date=value['inputs']['start_date'],end_date=value['inputs']['end_date'],
                     names=[p['source']['name'] for p in value['result']['profiles']])
        for kind, record in (('asset_analysis',value),('asset_analysis_summary',summary)):
            self.db.execute('INSERT INTO records VALUES(?,?,?)',(kind,value['id'],json.dumps(record,ensure_ascii=False,allow_nan=False,separators=(',',':'))))

    def asset_analysis_history(self, offset, limit):
        return [json.loads(r[0]) for r in self.db.execute("SELECT body FROM records WHERE kind='asset_analysis_summary' ORDER BY rowid DESC LIMIT ? OFFSET ?",(limit,offset))]

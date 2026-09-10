"""D6 persistence: immutable FX, price versions, portfolio bindings and NAV cuts.

No data is invented during migration. Schema 5 also prevents D5 from opening
books that now contain explicit currency exchanges or USD corporate events.
"""
import json


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


class ValuationWork:
    def market_head(self, kind, ident):
        if kind == 'prices':
            row = self.db.execute("SELECT json_extract(body,'$.version') FROM records WHERE kind IN ('dataset','native_price') AND id=?", (ident,)).fetchone()
        else:
            row = self.db.execute("SELECT json_extract(body,'$.version') FROM fx_series WHERE id=?", (ident,)).fetchone()
        return row[0] if row else None

    def valuation_stamp(self, ident, revision=None):
        portfolio = self.portfolio_record(ident, revision)
        fx = self.portfolio_fx(ident, portfolio['revision'])
        heads = sorted({b['dataset_id'] for b in portfolio['bindings']})
        return dict(portfolio_id=ident, portfolio_revision=portfolio['revision'], bindings=portfolio['bindings'], fx_binding=fx,
            catalog_revision=self.db.execute('SELECT COALESCE(MAX(revision),0) FROM catalog_revisions').fetchone()[0],
            corporate_revision=self.db.execute('SELECT (SELECT COUNT(*) FROM corporate_versions)+(SELECT COUNT(*) FROM corporate_sources)').fetchone()[0],
            price_heads=[[key,self.market_head('prices',key)] for key in heads],
            fx_head=self.market_head('fx',fx['series_id']) if fx else None)

    def market_current(self, kind, ident):
        if kind == 'prices':
            return self.get('native_price', ident)
        row = self.db.execute('SELECT body FROM fx_series WHERE id=?', (ident,)).fetchone()
        return json.loads(row[0]) if row else None

    def market_version(self, kind, ident, version):
        if kind == 'prices':
            value = self.dataset_version(ident, version)
            return value if value and value.get('format_id') == 'atlas-prices-v2' else None
        row = self.db.execute('SELECT body FROM fx_versions WHERE series_id=? AND revision=?', (ident, version)).fetchone()
        return json.loads(row[0]) if row else None

    def market_list(self):
        return self.list('native_price') + [json.loads(r[0]) for r in self.db.execute('SELECT body FROM fx_series ORDER BY rowid')]

    def save_market_version(self, value):
        payload = encoded(value)
        if value['kind'] == 'prices':
            # Reuse immutable dataset versions. Native observations remain out of
            # the legacy EUR research catalogue and its float normalization.
            self.db.execute('INSERT INTO versions VALUES(?,?,?)', (value['id'], value['version'], payload))
            self.put('native_price', value)
        else:
            self.db.execute("INSERT INTO fx_series VALUES(?,'USD','EUR',?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", (value['id'], payload))
            self.db.execute('INSERT INTO fx_versions VALUES(?,?,?)', (value['id'], value['version'], payload))

    def portfolio_fx(self, ident, revision):
        row = self.db.execute('SELECT body FROM portfolio_fx_versions WHERE portfolio_id=? AND revision<=? ORDER BY revision DESC LIMIT 1', (ident, revision)).fetchone()
        return json.loads(row[0]) if row else None

    def bind_portfolio_fx(self, portfolio, series):
        self.write_portfolio_revision(portfolio['id'], portfolio['event_ids'], portfolio['bindings'])
        updated = self.portfolio_record(portfolio['id'])
        value = dict(portfolio_id=portfolio['id'], portfolio_revision=updated['revision'], series_id=series['id'], series_version=series['version'])
        self.db.execute('INSERT INTO portfolio_fx_versions VALUES(?,?,?,?,?)', (portfolio['id'], updated['revision'], series['id'], series['version'], encoded(value)))
        return value

    def save_valuation(self, value):
        self.db.execute('INSERT INTO valuation_cuts VALUES(?,?,?,?,?)', (value['id'], value['portfolio_id'], value['portfolio_revision'], value['context_hash'], encoded(value)))

    def valuation(self, ident, cut_id):
        row = self.db.execute('SELECT body FROM valuation_cuts WHERE id=? AND portfolio_id=?', (cut_id, ident)).fetchone()
        return json.loads(row[0]) if row else None

    def valuations(self, ident, offset=0, limit=100):
        return [json.loads(row[0]) for row in self.db.execute('SELECT body FROM valuation_cuts WHERE portfolio_id=? ORDER BY rowid DESC LIMIT ? OFFSET ?', (ident, limit, offset))]


DDL = {
    'fx_series': "CREATE TABLE fx_series(id TEXT PRIMARY KEY NOT NULL, from_currency TEXT NOT NULL CHECK(from_currency='USD'), to_currency TEXT NOT NULL CHECK(to_currency='EUR'), body TEXT NOT NULL)",
    'fx_versions': "CREATE TABLE fx_versions(series_id TEXT NOT NULL REFERENCES fx_series(id), revision INTEGER NOT NULL CHECK(revision > 0), body TEXT NOT NULL, PRIMARY KEY(series_id,revision))",
    'portfolio_fx_versions': "CREATE TABLE portfolio_fx_versions(portfolio_id TEXT NOT NULL REFERENCES portfolios(id), revision INTEGER NOT NULL CHECK(revision > 0), series_id TEXT NOT NULL, series_revision INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(portfolio_id,revision), FOREIGN KEY(series_id,series_revision) REFERENCES fx_versions(series_id,revision))",
    'valuation_cuts': "CREATE TABLE valuation_cuts(id TEXT PRIMARY KEY NOT NULL, portfolio_id TEXT NOT NULL, portfolio_revision INTEGER NOT NULL, context_hash TEXT NOT NULL, body TEXT NOT NULL, FOREIGN KEY(portfolio_id,portfolio_revision) REFERENCES portfolio_revisions(portfolio_id,revision))",
}


def validate_schema(db):
    for table, ddl in DDL.items():
        row = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not row or row[0] != ddl:
            raise ValueError(f'Esquema incompatible en {table}; no se ha migrado la base.')
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('Referencias de FX/valoración inválidas.')


def migrate_v5(db):
    for ddl in DDL.values():
        db.execute(ddl)
    validate_schema(db)
    db.execute('PRAGMA user_version=5')

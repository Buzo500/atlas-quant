"""Additive D6 schema boundary; series and NAV use cases arrive in D6.3/4.

No data is invented during migration. Schema 5 also prevents D5 from opening
books that now contain explicit currency exchanges or USD corporate events.
"""
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

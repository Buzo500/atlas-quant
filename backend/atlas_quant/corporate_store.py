"""Additive D5 persistence. All methods run in the caller's Store transaction."""
import json
from .identity_store import encoded

DDL = {
    "corporate_events": "CREATE TABLE corporate_events(id TEXT PRIMARY KEY NOT NULL, listing_id TEXT NOT NULL REFERENCES listings(id), body TEXT NOT NULL)",
    "corporate_versions": "CREATE TABLE corporate_versions(event_id TEXT NOT NULL REFERENCES corporate_events(id), revision INTEGER NOT NULL CHECK(revision > 0), body TEXT NOT NULL, PRIMARY KEY(event_id,revision))",
    "corporate_sources": "CREATE TABLE corporate_sources(source TEXT NOT NULL, external_id TEXT NOT NULL, event_id TEXT NOT NULL REFERENCES corporate_events(id), body TEXT NOT NULL, PRIMARY KEY(source,external_id))",
    "corporate_applications": "CREATE TABLE corporate_applications(portfolio_id TEXT NOT NULL REFERENCES portfolios(id), event_id TEXT NOT NULL REFERENCES corporate_events(id), revision INTEGER NOT NULL CHECK(revision > 0), portfolio_revision INTEGER NOT NULL CHECK(portfolio_revision > 0), body TEXT NOT NULL, PRIMARY KEY(portfolio_id,event_id,revision))",
    "corporate_documents": "CREATE TABLE corporate_documents(id TEXT PRIMARY KEY NOT NULL, portfolio_id TEXT REFERENCES portfolios(id), body TEXT NOT NULL)",
}


def validate_schema(db):
    for table, ddl in DDL.items():
        row = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not row or row[0] != ddl:
            raise ValueError(f"Esquema incompatible en {table}; no se ha migrado la base.")
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Referencias de eventos corporativos inválidas.")


def migrate_v4(db):
    for ddl in DDL.values():
        db.execute(ddl)
    validate_schema(db)
    db.execute("PRAGMA user_version=4")


class CorporateWork:
    def corporate_state(self):
        versions = [json.loads(r[0]) for r in self.db.execute(
            "SELECT v.body FROM corporate_versions v WHERE v.revision=(SELECT MAX(c.revision) FROM corporate_versions c WHERE c.event_id=v.event_id) ORDER BY v.event_id")]
        sources = [json.loads(r[0]) for r in self.db.execute(
            "SELECT body FROM corporate_sources ORDER BY source,external_id")]
        latest = {}
        for event in versions:
            latest[event["id"]] = event
        count = self.db.execute("SELECT COUNT(*) FROM corporate_versions").fetchone()[0]
        return dict(events=list(latest.values()), sources=sources, revision=count + len(sources))

    def corporate_version(self, ident, revision):
        row = self.db.execute("SELECT body FROM corporate_versions WHERE event_id=? AND revision=?", (ident, revision)).fetchone()
        return json.loads(row[0]) if row else None

    def save_corporate_event(self, value):
        if value["revision"] == 1:
            self.db.execute("INSERT INTO corporate_events VALUES(?,?,?)", (value["id"], value["listing_id"],
                encoded(dict(id=value["id"], listing_id=value["listing_id"]))))
        self.db.execute("INSERT INTO corporate_versions VALUES(?,?,?)", (value["id"], value["revision"], encoded(value)))

    def save_corporate_source(self, value):
        self.db.execute("INSERT INTO corporate_sources VALUES(?,?,?,?)", (value["source"], value["external_id"], value["event_id"], encoded(value)))

    def corporate_applications(self, portfolio_id, portfolio_revision=None):
        rows = self.db.execute("SELECT body FROM corporate_applications WHERE portfolio_id=? AND portfolio_revision<=? ORDER BY event_id,revision",
                               (portfolio_id, portfolio_revision if portfolio_revision is not None else 9223372036854775807))
        latest = {}
        for (body,) in rows:
            value = json.loads(body)
            latest[value["event_id"]] = value
        return list(latest.values())

    def save_corporate_application(self, ident, revision, value):
        value = {**value, "portfolio_revision": revision}
        self.db.execute("INSERT INTO corporate_applications VALUES(?,?,?,?,?)",
            (ident, value["event_id"], value["revision"], revision, encoded(value)))

    def save_corporate_document(self, value):
        self.db.execute("INSERT INTO corporate_documents VALUES(?,?,?)", (value["id"], value.get("portfolio_id"), encoded(value)))

    def corporate_document(self, ident):
        row = self.db.execute("SELECT body FROM corporate_documents WHERE id=?", (ident,)).fetchone()
        return json.loads(row[0]) if row else None

    def corporate_documents(self, portfolio_id, offset, limit):
        total = self.db.execute("SELECT COUNT(*) FROM corporate_documents WHERE portfolio_id IS ?", (portfolio_id,)).fetchone()[0]
        rows = self.db.execute("SELECT json_object('id', id, 'portfolio_id', portfolio_id, 'kind', json_extract(body, '$.kind'), 'created_at', json_extract(body, '$.created_at')) FROM corporate_documents WHERE portfolio_id IS ? ORDER BY rowid DESC LIMIT ? OFFSET ?", (portfolio_id, limit, offset))
        return total, [json.loads(r[0]) for r in rows]

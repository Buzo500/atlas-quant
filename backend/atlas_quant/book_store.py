"""D4 additive schema and persistence, called only within Store transactions."""
import json

from .identity_store import encoded

DDL = {
    "book_entries": "CREATE TABLE book_entries(portfolio_id TEXT NOT NULL REFERENCES portfolios(id), id TEXT NOT NULL, external_key TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision > 0), listing_id TEXT REFERENCES listings(id), body TEXT NOT NULL, PRIMARY KEY(portfolio_id,id), UNIQUE(portfolio_id,external_key,revision))",
    "book_documents": "CREATE TABLE book_documents(portfolio_id TEXT NOT NULL REFERENCES portfolios(id), id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('import','reconciliation','correction')), body TEXT NOT NULL, PRIMARY KEY(portfolio_id,id))",
    "book_sources": "CREATE TABLE book_sources(portfolio_id TEXT NOT NULL REFERENCES portfolios(id), source TEXT NOT NULL, source_account TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(portfolio_id,source))",
}


def validate_schema(db):
    for table, statement in DDL.items():
        found = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not found or found[0] != statement:
            raise ValueError(f"Esquema incompatible en {table}; no se ha migrado la base.")
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Referencias de libro inválidas.")


def migrate_v3(db):
    for statement in DDL.values():
        db.execute(statement)
    validate_schema(db)
    db.execute("PRAGMA user_version=3")


class BookWork:
    def native_entries(self, ident):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT body FROM book_entries WHERE portfolio_id=? ORDER BY rowid", (ident,))]

    def insert_native_entry(self, portfolio_id, item):
        event = item["event"]
        self.db.execute("INSERT INTO book_entries VALUES(?,?,?,?,?,?)",
                        (portfolio_id, event["id"], event["external_key"], event["revision"],
                         item["listing_id"], encoded(item)))

    def book_sources(self, ident):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT body FROM book_sources WHERE portfolio_id=? ORDER BY source", (ident,))]

    def bind_book_source(self, ident, source, account):
        self.db.execute("INSERT OR IGNORE INTO book_sources VALUES(?,?,?,?)",
                        (ident, source, account, encoded(dict(source=source, source_account=account))))

    def book_document(self, ident, document_id):
        row = self.db.execute("SELECT body FROM book_documents WHERE portfolio_id=? AND id=?",
                              (ident, document_id)).fetchone()
        return json.loads(row[0]) if row else None

    def save_book_document(self, ident, value):
        self.db.execute("INSERT INTO book_documents VALUES(?,?,?,?)",
                        (ident, value["id"], value["kind"], encoded(value)))

    def book_documents(self, ident, offset=0, limit=100):
        count = self.db.execute("SELECT COUNT(*) FROM book_documents WHERE portfolio_id=?", (ident,)).fetchone()[0]
        rows = self.db.execute("SELECT body FROM book_documents WHERE portfolio_id=? ORDER BY rowid DESC LIMIT ? OFFSET ?",
                               (ident, limit, offset))
        return count, [json.loads(r[0]) for r in rows]

"""SQLite persistence for D2. Used only inside Store's UnitOfWork transaction."""
from __future__ import annotations

import json
from collections import Counter
from uuid import uuid4
from .analytics import iso_date, symbol_value


DDL = {
    "instruments": "CREATE TABLE instruments(id TEXT PRIMARY KEY NOT NULL, body TEXT NOT NULL)",
    "listings": "CREATE TABLE listings(id TEXT PRIMARY KEY NOT NULL, instrument_id TEXT NOT NULL REFERENCES instruments(id), currency TEXT NOT NULL CHECK(currency IN ('EUR','USD')), market TEXT, body TEXT NOT NULL)",
    "listing_aliases": "CREATE TABLE listing_aliases(id TEXT PRIMARY KEY NOT NULL, listing_id TEXT NOT NULL REFERENCES listings(id), provider TEXT NOT NULL, symbol TEXT NOT NULL, valid_from TEXT, valid_to TEXT, source TEXT NOT NULL, CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from))",
    "catalog_revisions": "CREATE TABLE catalog_revisions(revision INTEGER PRIMARY KEY CHECK(revision > 0), body TEXT NOT NULL)",
    "portfolios": "CREATE TABLE portfolios(id TEXT PRIMARY KEY NOT NULL, legacy_dataset_id TEXT UNIQUE, body TEXT NOT NULL)",
    "portfolio_revisions": "CREATE TABLE portfolio_revisions(portfolio_id TEXT NOT NULL REFERENCES portfolios(id), revision INTEGER NOT NULL CHECK(revision > 0), body TEXT NOT NULL, PRIMARY KEY(portfolio_id,revision))",
    "ledger_entries": "CREATE TABLE ledger_entries(portfolio_id TEXT NOT NULL REFERENCES portfolios(id), event_id TEXT NOT NULL, listing_id TEXT REFERENCES listings(id), effective_date TEXT NOT NULL, day_sequence INTEGER NOT NULL CHECK(day_sequence > 0), body TEXT NOT NULL, PRIMARY KEY(portfolio_id,event_id), UNIQUE(portfolio_id,effective_date,day_sequence))",
}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def validate_schema(db):
    # Exact DDL includes FKs, CHECKs and UNIQUEs, not just column names.
    for table, statement in DDL.items():
        row = db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not row or row[0] != statement:
            raise ValueError(f"Esquema incompatible en {table}; no se ha migrado la base.")
    if db.execute("PRAGMA foreign_key_check").fetchone():
        raise ValueError("Referencias de identidad o cartera inválidas.")


class IdentityWork:
    """Mixin: self.db, get/list/audit belong to UnitOfWork; no nested transactions."""

    def catalog(self, revision=None):
        if revision is not None:
            row = self.db.execute("SELECT body FROM catalog_revisions WHERE revision=?", (revision,)).fetchone()
            if row is None:
                raise KeyError("Revisión de catálogo no encontrada.")
            return json.loads(row[0])
        instruments = [json.loads(r[0]) for r in self.db.execute("SELECT body FROM instruments ORDER BY id")]
        listings = [json.loads(r[0]) for r in self.db.execute("SELECT body FROM listings ORDER BY id")]
        aliases = [dict(zip(("id", "listing_id", "provider", "symbol", "valid_from", "valid_to", "source"), r))
                   for r in self.db.execute("SELECT * FROM listing_aliases ORDER BY id")]
        revision = self.db.execute("SELECT COALESCE(MAX(revision),0) FROM catalog_revisions").fetchone()[0]
        return dict(revision=revision, instruments=instruments, listings=listings, aliases=aliases)

    def save_catalog_revision(self):
        value = self.catalog()
        value["revision"] += 1
        self.db.execute("INSERT INTO catalog_revisions VALUES(?,?)", (value["revision"], encoded(value)))
        return value

    def insert_instrument(self, fields):
        value = {**fields, "id": uuid4().hex}
        self.db.execute("INSERT INTO instruments VALUES(?,?)", (value["id"], encoded(value)))
        return value

    def insert_listing(self, fields):
        value = {**fields, "id": uuid4().hex}
        self.db.execute("INSERT INTO listings VALUES(?,?,?,?,?)", (
            value["id"], value["instrument_id"], value["currency"], value.get("market"), encoded(value)))
        return value

    def insert_alias(self, fields):
        value = {**fields, "id": uuid4().hex}
        self.db.execute("INSERT INTO listing_aliases VALUES(?,?,?,?,?,?,?)", tuple(value.get(k) for k in
            ("id", "listing_id", "provider", "symbol", "valid_from", "valid_to", "source")))
        return value

    def local_identities(self, dataset_id, symbols):
        symbols = {symbol_value(symbol) for symbol in symbols}
        existing = {item["legacy_symbol"]: item for item in self.catalog()["listings"]
                    if item.get("legacy_dataset_id") == dataset_id}
        changed = False
        for symbol in sorted(set(symbols) - existing.keys()):
            instrument = self.insert_instrument(dict(name=symbol, instrument_type="unknown", codes=[],
                                                     source="Migración/importación local", verified=False))
            listing = self.insert_listing(dict(instrument_id=instrument["id"], currency="EUR", market=None,
                calendar=None, verified=False, legacy_dataset_id=dataset_id, legacy_symbol=symbol))
            self.insert_alias(dict(listing_id=listing["id"], provider="legacy:" + dataset_id, symbol=symbol,
                valid_from=None, valid_to=None, source="Símbolo declarado en el conjunto local"))
            existing[symbol] = listing
            changed = True
        if changed:
            self.save_catalog_revision()
        return existing

    def legacy_portfolio_id(self, dataset_id):
        row = self.db.execute("SELECT id FROM portfolios WHERE legacy_dataset_id=?", (dataset_id,)).fetchone()
        return row[0] if row else None

    def portfolio_record(self, ident, revision=None):
        row = self.db.execute("SELECT body FROM portfolios WHERE id=?", (ident,)).fetchone()
        if row is None:
            raise KeyError("Cartera no encontrada.")
        if revision is None:
            saved = self.db.execute("SELECT revision,body FROM portfolio_revisions WHERE portfolio_id=? ORDER BY revision DESC LIMIT 1", (ident,)).fetchone()
        else:
            saved = self.db.execute("SELECT revision,body FROM portfolio_revisions WHERE portfolio_id=? AND revision=?", (ident, revision)).fetchone()
        if saved is None:
            raise KeyError("Revisión de cartera no encontrada.")
        return {**json.loads(row[0]), **json.loads(saved[1]), "revision": saved[0]}

    def portfolio_list(self):
        return [self.portfolio_record(r[0]) for r in self.db.execute("SELECT id FROM portfolios ORDER BY rowid")]

    def portfolio_events(self, portfolio):
        if portfolio["accounting_policy"] == "atlas-accounting-v2":
            rows = {item["event"]["id"]: item for item in self.native_entries(portfolio["id"])}
            return [rows[ident] for ident in portfolio["event_ids"]]
        rows = {r[0]: dict(event=json.loads(r[4]), listing_id=r[1], date=r[2], day_sequence=r[3])
                for r in self.db.execute("SELECT event_id,listing_id,effective_date,day_sequence,body FROM ledger_entries WHERE portfolio_id=?", (portfolio["id"],))}
        return [rows[ident] for ident in portfolio["event_ids"]]

    def create_portfolio(self, name, legacy_dataset_id=None, bindings=None, accounting_policy="legacy-eur-v1"):
        if accounting_policy not in {"legacy-eur-v1", "atlas-accounting-v2"} or (legacy_dataset_id and accounting_policy != "legacy-eur-v1"):
            raise ValueError("Política contable no compatible con el origen de cartera.")
        value = dict(id=uuid4().hex, name=name, base_currency="EUR", account_id=uuid4().hex,
                     accounting_policy=accounting_policy, legacy_dataset_id=legacy_dataset_id)
        self.db.execute("INSERT INTO portfolios VALUES(?,?,?)", (value["id"], legacy_dataset_id, encoded(value)))
        self.write_portfolio_revision(value["id"], [], bindings or [])
        return self.portfolio_record(value["id"])

    def write_portfolio_revision(self, ident, event_ids, bindings):
        revision = self.db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM portfolio_revisions WHERE portfolio_id=?", (ident,)).fetchone()[0]
        self.db.execute("INSERT INTO portfolio_revisions VALUES(?,?,?)", (ident, revision,
            encoded(dict(event_ids=event_ids, bindings=bindings, catalog_revision=self.catalog()["revision"]))))

    def append_entries(self, portfolio, entries):
        if portfolio["accounting_policy"] != "legacy-eur-v1":
            raise ValueError("El libro v2 requiere la importación de movimientos v2.")
        current = self.portfolio_events(portfolio)
        known = {item["event"]["id"]: item for item in current}
        sequence = Counter(item["date"] for item in current)
        added = 0
        for item in entries:
            event, listing_id = item["event"], item["listing_id"]
            if event["id"] in known:
                previous = known[event["id"]]
                if previous["event"] != event or previous["listing_id"] != listing_id:
                    raise ValueError("Un ID de movimiento ya existe con datos o identidad distintos.")
                continue
            sequence[event["date"]] += 1
            self.db.execute("INSERT INTO ledger_entries VALUES(?,?,?,?,?,?)", (portfolio["id"], event["id"],
                listing_id, event["date"], sequence[event["date"]], encoded(event)))
            saved = dict(event=event, listing_id=listing_id, date=event["date"], day_sequence=sequence[event["date"]])
            current.append(saved)
            known[event["id"]] = saved
            added += 1
        if added:
            current.sort(key=lambda item: (item["date"], item["day_sequence"]))
            self.write_portfolio_revision(portfolio["id"], [item["event"]["id"] for item in current], portfolio["bindings"])
        return added

    def put_legacy_ledger(self, value):
        dataset_id = value["id"]
        events = value.get("events", [])
        for event in events:
            if not isinstance(event.get("id"), str) or not event["id"].strip():
                raise ValueError("Cada movimiento necesita un ID original no vacío.")
            iso_date(event.get("date"))
        if len({event["id"] for event in events}) != len(events):
            raise ValueError("El libro contiene IDs de movimientos duplicados.")
        dataset = self.get("dataset", dataset_id) or {}
        symbols = {b["symbol"] for b in dataset.get("bars", [])} | {e["symbol"] for e in events if e.get("symbol")}
        identities = self.local_identities(dataset_id, symbols)
        ident = self.legacy_portfolio_id(dataset_id)
        if ident is None:
            bindings = [dict(listing_id=identities[symbol_value(symbol)]["id"], dataset_id=dataset_id,
                dataset_version=dataset["version"], symbol=symbol) for symbol in sorted({b["symbol"] for b in dataset.get("bars", [])})]
            portfolio = self.create_portfolio(dataset.get("name", "Cartera importada"), dataset_id, bindings)
        else:
            portfolio = self.portfolio_record(ident)
            if not set(portfolio["event_ids"]).issubset({event["id"] for event in events}):
                raise ValueError("No se pueden borrar movimientos del libro; requiere una corrección revisada.")
        # Migration preserves the stable date order used by the legacy engine.
        ordered = sorted(events, key=lambda event: event["date"])
        self.append_entries(portfolio, [dict(event=e, listing_id=identities[symbol_value(e["symbol"])]["id"] if e.get("symbol") else None) for e in ordered])
        return value


def migrate_v2(work):
    for statement in DDL.values():
        work.db.execute(statement)
    for dataset in work.list("dataset"):
        work.local_identities(dataset["id"], {bar["symbol"] for bar in dataset.get("bars", [])})
    # Read the archive directly; the runtime compatibility adapter reads the new book.
    for row in work.db.execute("SELECT body FROM records WHERE kind='ledger' ORDER BY rowid").fetchall():
        work.put_legacy_ledger(json.loads(row[0]))
    validate_schema(work.db)
    work.db.execute("PRAGMA user_version=2")

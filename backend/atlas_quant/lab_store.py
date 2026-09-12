"""Small metadata queries; frozen research records never update portfolio books."""
import json


class LabWork:
    def robustness_candidate(self, ident, revision):
        # Project only the revision's development references; no holdout evidence.
        row = self.db.execute("""SELECT json_extract(body,'$.revision_hash'),
            json_extract(body,'$.protocol_ids'), (SELECT json_group_array(json_object(
                'protocol_id',json_extract(value,'$.protocol.id'),
                'development_hash',json_extract(value,'$.development_hash')))
                FROM json_each(body,'$.evidence'))
            FROM records WHERE kind='candidate_revision' AND id=?""", (f'{ident}:{revision}',)).fetchone()
        return dict(revision_hash=row[0], protocol_ids=json.loads(row[1]), evidence=json.loads(row[2])) if row else None

    def robustness_development(self, ident):
        # SQLite filters the frozen calendar before handing it to the statistics
        # layer. No frozen bars, openings or final-period results are retrieved.
        row = self.db.execute("""SELECT json_extract(body,'$.protocol'),
            json_extract(body,'$.config'),json_extract(body,'$.development'),
            json_extract(body,'$.frozen.source'),json_extract(body,'$.evidence_hash'),
            (SELECT json_group_array(json_extract(value,'$.date'))
             FROM json_each(body,'$.frozen.calendar.sessions')
             WHERE json_extract(value,'$.date') < json_extract(body,'$.protocol.holdout_date'))
            FROM records WHERE kind='lab_protocol' AND id=?""", (ident,)).fetchone()
        if row is None:
            return None
        return dict(protocol=json.loads(row[0]), config=json.loads(row[1]), development=json.loads(row[2]),
                    source=json.loads(row[3]), evidence_hash=row[4], session_dates=json.loads(row[5]))

    def robustness_history(self, candidate, offset, limit):
        return [json.loads(r[0]) for r in self.db.execute("""SELECT json_extract(body,'$.report') FROM records
            WHERE kind='robustness_report' AND json_extract(body,'$.report.request.candidate_id')=?
            ORDER BY rowid DESC LIMIT ? OFFSET ?""", (candidate, limit, offset))]

    def candidate_search(self, query, status, offset, limit):
        # Literal Unicode case-insensitive search, including previous decisions.
        self.db.create_function('atlas_casefold', 1, lambda s: (s or '').casefold(), deterministic=True)
        return [json.loads(r[0]) for r in self.db.execute("""SELECT body FROM records
            WHERE kind='candidate_revision' AND (?='' OR json_extract(body,'$.status')=?)
            AND instr(atlas_casefold(json_extract(body,'$.name') || char(10) ||
                json_extract(body,'$.hypothesis') || char(10) || json_extract(body,'$.reason')), ?) > 0
            ORDER BY json_extract(body,'$.created_at') DESC,id LIMIT ? OFFSET ?""",
            (status, status, query.casefold(), limit, offset))]

    def candidate_history(self, offset, limit):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT body FROM records WHERE kind='candidate_summary' ORDER BY json_extract(body,'$.updated_at') DESC,id LIMIT ? OFFSET ?", (limit, offset))]

    def candidate_revisions(self, ident, offset, limit):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT body FROM records WHERE kind='candidate_revision' AND json_extract(body,'$.candidate_id')=? ORDER BY json_extract(body,'$.revision') DESC LIMIT ? OFFSET ?",
            (ident, limit, offset))]

    def lab_insert(self, kind, value):
        self.db.execute('INSERT INTO records VALUES(?,?,?)', (kind, value['id'], json.dumps(value, ensure_ascii=False, allow_nan=False)))

    def lab_history(self, offset, limit):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT body FROM records WHERE kind='lab_summary' ORDER BY rowid DESC LIMIT ? OFFSET ?", (limit, offset))]

    def lab_overlaps(self, kind, instrument, start, end, exclude=None):
        return self.db.execute("""SELECT 1 FROM records WHERE kind=? AND id!=?
            AND json_extract(body,'$.instrument_id')=?
            AND json_extract(body,'$.start_date')<=? AND json_extract(body,'$.end_date')>=? LIMIT 1""",
            (kind, exclude or '', instrument, end, start)).fetchone() is not None

    def lab_reserved(self, instrument, start, end, exclude):
        # An exposed final period may later be used for development. It can
        # never become unseen again, and contaminated sibling reservations no
        # longer prevent this legitimate reuse of already-visible history.
        return self.db.execute("""SELECT 1 FROM records r WHERE r.kind='lab_reservation' AND r.id!=?
            AND json_extract(r.body,'$.instrument_id')=?
            AND json_extract(r.body,'$.start_date')<=? AND json_extract(r.body,'$.end_date')>=?
            AND NOT EXISTS (SELECT 1 FROM records e WHERE e.kind='lab_exposure'
                AND json_extract(e.body,'$.instrument_id')=json_extract(r.body,'$.instrument_id')
                AND json_extract(e.body,'$.start_date')<=json_extract(r.body,'$.end_date')
                AND json_extract(e.body,'$.end_date')>=json_extract(r.body,'$.start_date')) LIMIT 1""",
            (exclude, instrument, end, start)).fetchone() is not None

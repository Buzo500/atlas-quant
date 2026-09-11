"""Small metadata queries; frozen research records never update portfolio books."""
import json


class LabWork:
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

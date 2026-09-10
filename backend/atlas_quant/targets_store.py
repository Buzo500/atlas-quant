"""Analytical records on schema 5; one CAS-protected head per portfolio."""
import json


class TargetsWork:
    def targets_head(self, portfolio):
        return self.get('targets_head', portfolio, dict(id=portfolio, revision=0, next_version=1, active_id=None))

    def target_set(self, portfolio, ident):
        value = self.get('target_set', ident)
        return value if value and value['portfolio_id'] == portfolio else None

    def insert_target_record(self, kind, value):
        self.db.execute('INSERT INTO records VALUES(?,?,?)',
            (kind, value['id'], json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))))

    def target_history(self, kind, portfolio, offset, limit):
        return [json.loads(row[0]) for row in self.db.execute(
            "SELECT body FROM records WHERE kind=? AND json_extract(body,'$.portfolio_id')=? ORDER BY rowid DESC LIMIT ? OFFSET ?",
            (kind, portfolio, limit, offset))]

    def target_report(self, portfolio, ident):
        value = self.get('target_report', ident)
        return value if value and value['portfolio_id'] == portfolio else None

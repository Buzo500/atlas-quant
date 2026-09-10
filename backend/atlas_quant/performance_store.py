"""Immutable reports in the existing generic record store; schema 5 unchanged."""
import json


class PerformanceWork:
    def save_performance(self, value):
        summary = {k:value[k] for k in ('id','portfolio_id','portfolio_revision','start_date','end_date','created_at','pnl')}
        summary.update({k:{field:value[k][field] for field in ('value','status','reasons')} for k in ('twr','mwr')})
        for kind, body in (('performance_report',value), ('performance_summary',summary)):
            self.db.execute('INSERT INTO records VALUES(?,?,?)', (kind,value['id'],json.dumps(body,ensure_ascii=False,allow_nan=False,separators=(',',':'))))

    def performance(self, portfolio, ident):
        value = self.get('performance_report', ident)
        return value if value and value['portfolio_id'] == portfolio else None

    def performance_history(self, portfolio, offset, limit):
        return [json.loads(row[0]) for row in self.db.execute("SELECT body FROM records WHERE kind='performance_summary' AND json_extract(body,'$.portfolio_id')=? ORDER BY rowid DESC LIMIT ? OFFSET ?", (portfolio,limit,offset))]

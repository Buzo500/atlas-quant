"""Immutable analytical records, independent of book and target activation."""
import json


class PlanningWork:
    def planning_report(self,portfolio,ident):
        value=self.get('planning_report',ident)
        return value if value and value['portfolio_id']==portfolio else None

    def save_planning(self,value):
        summary={k:value[k] for k in ('id','portfolio_id','created_at')}
        summary['kind']=value['result']['kind']
        for kind,record in (('planning_report',value),('planning_summary',summary)):
            self.db.execute('INSERT INTO records VALUES(?,?,?)',(kind,value['id'],json.dumps(record,ensure_ascii=False,allow_nan=False,separators=(',',':'))))

    def planning_history(self,portfolio,offset,limit):
        return [json.loads(r[0]) for r in self.db.execute("SELECT body FROM records WHERE kind='planning_summary' AND json_extract(body,'$.portfolio_id')=? ORDER BY rowid DESC LIMIT ? OFFSET ?",(portfolio,limit,offset))]

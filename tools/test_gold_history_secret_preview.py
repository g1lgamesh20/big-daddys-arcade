import copy
import unittest
from datetime import datetime, timezone, timedelta
from gold_history_secret_preview import preview
from gold_holder_history import evaluate

T0=datetime(2026,11,24,20,tzinfo=timezone.utc)
def row(sid,player,score):
    return {'id':str(sid),'name':player,'game':'A','gameName':'Robotron','score':score}
def history():
    return evaluate([row(1,'DON',100),row(2,'RDG',90)],None,set(),T0)[0]
def advance(state, rows, known, minutes):
    return evaluate(rows,state,set(map(str,known)),T0+timedelta(minutes=minutes))[0]
class GoldHistorySecretPreviewTests(unittest.TestCase):
    def test_baseline_has_no_comeback(self):
        self.assertEqual(preview(history(),T0)['comeback_evidence'],[])
    def test_loss_then_reclaim_is_evidence(self):
        s=history()
        s=advance(s,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)],[1,2],30)
        s=advance(s,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150),row(4,'DON',200)],[1,2,3],60)
        report=preview(s,T0+timedelta(hours=2))
        self.assertEqual(len(report['comeback_evidence']),1)
        self.assertEqual(report['comeback_evidence'][0]['player'],'DON')
    def test_tie_does_not_prove_reclaim(self):
        s=history()
        s=advance(s,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)],[1,2],30)
        s=advance(s,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150),row(4,'DON',150)],[1,2,3],60)
        self.assertEqual(preview(s,T0+timedelta(hours=2))['comeback_evidence'],[])
    def test_24_hour_candidate_only_after_24h(self):
        s=history()
        self.assertEqual(preview(s,T0+timedelta(hours=23))['king_day_candidates'],[])
        self.assertEqual(preview(s,T0+timedelta(hours=24))['king_day_candidates'],[])
        s=advance(s,[row(1,'DON',100),row(2,'RDG',90)],[1,2],1440)
        result=preview(s,T0+timedelta(hours=24))
        self.assertEqual([x['player'] for x in result['king_day_candidates']],['DON'])
        self.assertEqual(result['mode'],'PREVIEW_ONLY_NO_AWARDS')
    def test_new_takeover_resets_24h_candidate(self):
        s=history()
        s=advance(s,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)],[1,2],60)
        self.assertEqual(preview(s,T0+timedelta(hours=24))['king_day_candidates'],[])
        self.assertEqual(preview(s,T0+timedelta(hours=25))['king_day_candidates'],[])
        s=advance(s,[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)],[1,2,3],1500)
        self.assertEqual(preview(s,T0+timedelta(hours=25))['king_day_candidates'][0]['player'],'RDG')
    def test_missing_winner_cannot_confirm_tenure(self):
        s=history()
        s=advance(s,[row(3,'RDG',150)],[1,2],1500)
        self.assertEqual(preview(s,T0+timedelta(hours=25))['king_day_candidates'],[])
    def test_invalid_history_fails_closed(self):
        with self.assertRaises(ValueError):preview({'schema_version':1,'transitions':[]},T0)
    def test_does_not_mutate_history(self):
        s=history(); before=copy.deepcopy(s)
        preview(s,T0+timedelta(days=2))
        self.assertEqual(s,before)
if __name__=='__main__':unittest.main()

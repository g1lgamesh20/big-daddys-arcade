import copy,unittest
from datetime import datetime,timezone
from double_trouble_preview import preview
from double_trouble_activate import activate
def journal():
    return {'schema_version':1,'policy':'post_2026_11_19_approved_iscored_scores','scores':{
        '10':{'score_id':'10','name':'DON','game':'A','score':200,'date':'2026-11-25T10:00:00-05:00','first_observed_at':'2026-11-25T16:00:00+00:00'},
        '11':{'score_id':'11','name':'DON','game':'B','score':300,'date':'2026-11-25T11:00:00-05:00','first_observed_at':'2026-11-25T17:00:00+00:00'}}}
def event(gid,sid,observed):
    return {'id':'takeover:'+sid,'type':'takeover','game_id':gid,'game':'Game '+gid,
        'previous_holders':['RDG'],'new_holders':['DON'],'gained_holders':['DON'],
        'lost_holders':['RDG'],'previous_score':100,'new_score':200 if gid=='A' else 300,
        'new_score_ids':[sid],'observed_at':observed}
def history():
    return {'schema_version':1,'policy':'observed_approved_snapshots_only','transitions':[
        event('A','10','2026-11-25T16:00:00+00:00'),
        event('B','11','2026-11-25T17:00:00+00:00')]}
def ledger():return {'schema_version':1,'awards':[],'verified_plays':[]}
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
class DoubleTroubleTests(unittest.TestCase):
    def test_two_games(self):self.assertEqual(len(preview(journal(),history())['candidates']),1)
    def test_award(self):
        result,added=activate(journal(),history(),ledger(),NOW,enabled=True)
        self.assertEqual(len(added),1);self.assertEqual(added[0]['type'],'secret_double_trouble')
    def test_idempotent(self):
        result,_=activate(journal(),history(),ledger(),NOW,enabled=True)
        same,added=activate(journal(),history(),result,NOW,enabled=True)
        self.assertEqual(added,[]);self.assertEqual(result,same)
    def test_off(self):self.assertEqual(activate(journal(),history(),ledger(),NOW),(ledger(),[]))
    def test_one_game(self):
        h=history();h['transitions'].pop()
        self.assertEqual(preview(journal(),h)['candidates'],[])
    def test_same_game(self):
        h=history();h['transitions'][1]['game_id']='A'
        j=journal();j['scores']['11']['game']='A'
        self.assertEqual(preview(j,h)['candidates'],[])
    def test_different_day(self):
        j=journal();j['scores']['11']['date']='2026-11-24T11:00:00-05:00'
        self.assertEqual(preview(j,history())['candidates'],[])
    def test_missing_approved_score(self):
        j=journal();del j['scores']['11']
        self.assertEqual(preview(j,history())['candidates'],[])
    def test_wrong_player(self):
        j=journal();j['scores']['11']['name']='SPC'
        self.assertEqual(preview(j,history())['candidates'],[])
    def test_tie_not_takeover(self):
        h=history();h['transitions'][1]['type']='tie_joined';h['transitions'][1]['new_score']=100
        self.assertEqual(preview(journal(),h)['candidates'],[])
    def test_bad_ledger(self):
        with self.assertRaises(ValueError):activate(journal(),history(),{},NOW,enabled=True)
    def test_duplicate_award(self):
        l=ledger();l['awards']=[{'id':'dup'},{'id':'dup'}]
        with self.assertRaises(ValueError):activate(journal(),history(),l,NOW,enabled=True)
    def test_no_mutation(self):
        j=journal();h=history();l=ledger();before=copy.deepcopy((j,h,l))
        activate(j,h,l,NOW,enabled=True);self.assertEqual((j,h,l),before)
    def test_naive_time(self):
        with self.assertRaises(ValueError):activate(journal(),history(),ledger(),datetime(2026,11,26),enabled=True)
if __name__=='__main__':unittest.main()

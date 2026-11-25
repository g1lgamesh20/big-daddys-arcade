import copy,unittest
from back_from_the_dead_preview import preview
def journal():
    return {'schema_version':1,'policy':'post_2026_11_19_approved_iscored_scores','scores':{'9':{'score_id':'9','name':'DON','game':'A','score':300,'date':'2026-11-25T10:00:00-05:00','first_observed_at':'2026-11-25T16:00:00+00:00'}}}
def history():
    return {'schema_version':1,'policy':'observed_approved_snapshots_only','transitions':[
        {'id':'lost','type':'takeover','game_id':'A','game':'Robotron','previous_holders':['DON'],'new_holders':['RDG'],'gained_holders':['RDG'],'lost_holders':['DON'],'previous_score':100,'new_score':200,'new_score_ids':['8'],'observed_at':'2026-11-24T16:00:00+00:00'},
        {'id':'reclaimed','type':'takeover','game_id':'A','game':'Robotron','previous_holders':['RDG'],'new_holders':['DON'],'gained_holders':['DON'],'lost_holders':['RDG'],'previous_score':200,'new_score':300,'new_score_ids':['9'],'observed_at':'2026-11-25T16:00:00+00:00'}]}
class ComebackTests(unittest.TestCase):
    def test_verified_loss_and_reclaim(self):
        x=preview(journal(),history())['candidates'];self.assertEqual(len(x),1);self.assertEqual(x[0]['id'],'back_from_the_dead:DON')
    def test_baseline_not_loss(self):
        h=history();h['transitions']=h['transitions'][1:];self.assertEqual(preview(journal(),h)['candidates'],[])
    def test_tie_not_reclaim(self):
        h=history();h['transitions'][1]['type']='tie_joined';h['transitions'][1]['new_score']=200;self.assertEqual(preview(journal(),h)['candidates'],[])
    def test_missing_approved_winner(self):
        j=journal();j['scores']={};self.assertEqual(preview(j,history())['candidates'],[])
    def test_mismatched_winning_score(self):
        j=journal();j['scores']['9']['score']=299;self.assertEqual(preview(j,history())['candidates'],[])
    def test_mismatched_player(self):
        j=journal();j['scores']['9']['name']='RDG';self.assertEqual(preview(j,history())['candidates'],[])
    def test_mismatched_game(self):
        j=journal();j['scores']['9']['game']='B';self.assertEqual(preview(j,history())['candidates'],[])
    def test_duplicate_transition_fails(self):
        h=history();h['transitions'].append(copy.deepcopy(h['transitions'][0]))
        with self.assertRaises(ValueError):preview(journal(),h)
    def test_bad_journal_fails(self):
        with self.assertRaises(ValueError):preview({},history())
    def test_no_mutation(self):
        j=journal();h=history();before=copy.deepcopy((j,h));preview(j,h);self.assertEqual((j,h),before)
if __name__=='__main__':unittest.main()

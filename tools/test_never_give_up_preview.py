import copy
import unittest
from never_give_up_preview import preview

def journal(count=5, winning=True, same_game=True, scores=None):
    rows={}
    for i in range(count):
        sid=str(i+1)
        rows[sid]={'score_id':sid,'name':'DON','game':'A' if same_game or i<4 else 'B',
            'gameName':'Robotron','score':(scores[i] if scores else 10+i),
            'date':f'2026-11-{20+i:02d}T12:00:00-05:00',
            'first_observed_at':'2026-12-01T00:00:00+00:00'}
    if winning:
        rows['99']={'score_id':'99','name':'DON','game':'A','gameName':'Robotron',
            'score':200,'date':'2026-11-26T12:00:00-05:00',
            'first_observed_at':'2026-12-01T00:00:00+00:00'}
    return {'schema_version':1,'policy':'post_2026_11_19_approved_iscored_scores','scores':rows}

def history(event_type='takeover',winner='99',before=100):
    return {'schema_version':1,'policy':'observed_approved_snapshots_only',
        'transitions':[{'id':'gold_transition:A:99','type':event_type,'game_id':'A',
            'game':'Robotron','previous_score':before,'new_score':200,
            'gained_holders':['DON'],'new_score_ids':[winner],
            'previous_observed_at':'2026-11-19T20:00:00+00:00',
            'observed_at':'2026-12-01T01:00:00+00:00'}]}

class NeverGiveUpTests(unittest.TestCase):
    def test_five_attempts_then_gold(self):
        r=preview(journal(),history())
        self.assertEqual(len(r['candidates']),1)
        self.assertEqual(r['candidates'][0]['prior_unsuccessful_score_ids'],['1','2','3','4','5'])
        self.assertEqual(r['candidates'][0]['id'],'never_give_up:DON')
    def test_four_attempts_not_enough(self):
        self.assertEqual(preview(journal(4),history())['candidates'],[])
    def test_different_game_does_not_count(self):
        self.assertEqual(preview(journal(same_game=False),history())['candidates'],[])
    def test_tie_not_gold_takeover(self):
        self.assertEqual(preview(journal(),history(event_type='tie_joined'))['candidates'],[])
    def test_unmatched_gold_id_not_enough(self):
        self.assertEqual(preview(journal(),history(winner='other'))['candidates'],[])
    def test_baseline_not_takeover(self):
        h=history();h['transitions']=[]
        self.assertEqual(preview(journal(),h)['candidates'],[])
    def test_prior_scores_must_be_below_previous_gold(self):
        self.assertEqual(preview(journal(scores=[101,102,103,104,105]),history())['candidates'],[])
    def test_attempts_before_gold_was_observed_do_not_count(self):
        h=history()
        h['transitions'][0]['previous_observed_at']='2026-11-23T20:00:00+00:00'
        self.assertEqual(preview(journal(),h)['candidates'],[])
    def test_missing_previous_gold_observation_fails_closed(self):
        h=history()
        del h['transitions'][0]['previous_observed_at']
        self.assertEqual(preview(journal(),h)['candidates'],[])
    def test_invalid_previous_gold_observation_fails_closed(self):
        h=history()
        h['transitions'][0]['previous_observed_at']='2026-12-02T00:00:00+00:00'
        with self.assertRaises(ValueError):preview(journal(),h)
    def test_invalid_journal_fails_closed(self):
        with self.assertRaises(ValueError):preview({},history())
    def test_duplicate_transition_fails_closed(self):
        h=history();h['transitions'].append(copy.deepcopy(h['transitions'][0]))
        with self.assertRaises(ValueError):preview(journal(),h)
    def test_no_mutation(self):
        j=journal();h=history();before=(copy.deepcopy(j),copy.deepcopy(h))
        preview(j,h)
        self.assertEqual((j,h),before)
    def test_no_gold_score_no_candidate(self):
        self.assertEqual(preview(journal(winning=False),history())['candidates'],[])

if __name__=='__main__':
    unittest.main()

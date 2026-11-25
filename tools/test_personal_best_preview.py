import copy
import unittest
from personal_best_preview import preview

def journal(rows):
    return {'schema_version':1,'policy':'post_2026_11_19_approved_iscored_scores',
            'scores':{r['score_id']:r for r in rows}}

def row(sid, score, date='2026-11-21T12:00:00-05:00', player='DON', game='50041'):
    return {'score_id':str(sid),'name':player,'game':game,'gameName':'Galaga',
            'score':score,'date':date,'first_observed_at':'2026-11-24T12:00:00+00:00'}

class PersonalBestPreviewTests(unittest.TestCase):
    def test_strict_improvement(self):
        data=journal([row(1,100),row(2,101,'2026-11-22T12:00:00-05:00')])
        out=preview(data)
        self.assertEqual(out['improvement_events'],1)
        self.assertEqual(out['examples'][0]['previous_best'],100)
    def test_equal_score_is_not_improvement(self):
        self.assertEqual(preview(journal([row(1,100),row(2,100,'2026-11-22T12:00:00-05:00')]))['improvement_events'],0)
    def test_lower_score_then_higher_than_record(self):
        data=journal([row(1,100),row(2,50,'2026-11-22T12:00:00-05:00'),row(3,110,'2026-11-23T12:00:00-05:00')])
        self.assertEqual(preview(data)['improvement_events'],1)
    def test_separate_player_and_game(self):
        data=journal([row(1,100),row(2,200,'2026-11-22T12:00:00-05:00',player='VJG'),row(3,300,'2026-11-22T12:00:00-05:00',game='50042')])
        self.assertEqual(preview(data)['improvement_events'],0)
    def test_order_independent_and_immutable(self):
        data=journal([row(2,150,'2026-11-22T12:00:00-05:00'),row(1,100)])
        original=copy.deepcopy(data)
        self.assertEqual(preview(data)['improvement_events'],1)
        self.assertEqual(data,original)
    def test_cutover_rejected(self):
        with self.assertRaises(ValueError):
            preview(journal([row(1,100,'2026-11-19T12:00:00-05:00')]))
    def test_bad_journal_fails_closed(self):
        with self.assertRaises(ValueError):
            preview({'schema_version':1,'scores':{}})
    def test_first_milestone_only_at_two_improvements(self):
        data=journal([row(1,100),row(2,200,'2026-11-22T12:00:00-05:00'),row(3,300,'2026-11-23T12:00:00-05:00')])
        self.assertEqual([a['milestone'] for a in preview(data)['milestones']],[1])
    def test_five_and_ten_milestones_and_unique_ids(self):
        rows=[row(i,100+i,f'2026-12-{i:02d}T12:00:00-05:00') for i in range(1,12)]
        for r in rows:r['first_observed_at']='2027-01-05T12:00:00+00:00'
        data=journal(rows)
        result=preview(data)
        self.assertEqual([a['milestone'] for a in result['milestones']],[1,5,10])
        self.assertEqual(len({a['id'] for a in result['milestones']}),3)
    def test_same_timestamp_is_not_proof_of_sequence(self):
        self.assertEqual(preview(journal([row(1,100),row(2,200)]))['improvement_events'],0)

if __name__=='__main__':
    unittest.main()

import unittest
from datetime import datetime, timezone, timedelta
from gold_holder_history import evaluate

NOW = datetime(2026, 11, 24, 21, tzinfo=timezone.utc)
def row(sid, player, score, game='A'):
    return {'id':str(sid),'name':player,'game':game,'gameName':'Robotron','score':score}
def baseline(rows):
    return evaluate(rows,None,set(),NOW)[0]

class GoldHolderHistoryTests(unittest.TestCase):
    def test_first_snapshot_is_quiet(self):
        state,events=evaluate([row(1,'DON',100)],None,set(),NOW)
        self.assertEqual(events,[])
        self.assertEqual(state['transitions'],[])
    def test_new_player_takeover_and_repeat(self):
        prior=baseline([row(1,'DON',100),row(2,'RDG',90)])
        rows=[row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)]
        state,events=evaluate(rows,prior,{'1','2'},NOW+timedelta(minutes=30))
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['type'],'takeover')
        self.assertEqual(events[0]['previous_holders'],['DON'])
        self.assertEqual(events[0]['new_holders'],['RDG'])
        again,duplicate=evaluate(rows,state,{'1','2','3'},NOW+timedelta(hours=1))
        self.assertEqual(duplicate,[])
        self.assertEqual(again['transitions'],state['transitions'])
    def test_reclaim_after_observed_takeover(self):
        first=baseline([row(1,'DON',100),row(2,'RDG',90)])
        second,_=evaluate([row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150)],first,{'1','2'},NOW)
        third,events=evaluate([row(1,'DON',100),row(2,'RDG',90),row(3,'RDG',150),row(4,'DON',180)],second,{'1','2','3'},NOW+timedelta(hours=1))
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['gained_holders'],['DON'])
        self.assertEqual(len(third['transitions']),2)
    def test_existing_holder_improvement_not_takeover(self):
        prior=baseline([row(1,'DON',100)])
        state,events=evaluate([row(1,'DON',100),row(2,'DON',120)],prior,{'1'},NOW)
        self.assertEqual(events,[])
        self.assertEqual(state['holders_by_game']['A']['score'],120)
    def test_old_score_cannot_backfill(self):
        prior=baseline([row(1,'DON',100)])
        state,events=evaluate([row(1,'DON',100),row(2,'RDG',150)],prior,{'1','2'},NOW)
        self.assertEqual(events,[])
        self.assertEqual(state['holders_by_game']['A']['holders'],['DON'])
    def test_missing_old_winner_preserves_baseline(self):
        prior=baseline([row(1,'DON',100)])
        state,events=evaluate([row(2,'RDG',150)],prior,{'1'},NOW)
        self.assertEqual(events,[])
        self.assertEqual(state['holders_by_game']['A']['holders'],['DON'])
    def test_tied_gold_joined(self):
        prior=baseline([row(1,'DON',100)])
        state,events=evaluate([row(1,'DON',100),row(2,'RDG',100)],prior,{'1'},NOW)
        self.assertEqual(events[0]['type'],'tie_joined')
        self.assertEqual(state['holders_by_game']['A']['holders'],['DON','RDG'])
    def test_no_exact_time_inference(self):
        prior=baseline([row(1,'DON',100)])
        _,events=evaluate([row(1,'DON',100),row(2,'RDG',150)],prior,{'1'},NOW+timedelta(hours=1))
        self.assertEqual(events[0]['time_policy'],'observed_between_refreshes_not_exact_takeover_time')
    def test_invalid_history_refuses_reset(self):
        with self.assertRaises(ValueError):
            evaluate([row(1,'DON',100)],{'schema_version':1,'holders_by_game':{}},set(),NOW)
    def test_empty_feed_refuses_reset(self):
        with self.assertRaises(ValueError):
            evaluate([],None,set(),NOW)
if __name__=='__main__': unittest.main()

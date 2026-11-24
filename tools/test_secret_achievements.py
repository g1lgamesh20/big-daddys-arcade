import copy
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from secret_achievements import evaluate

ET = ZoneInfo('America/New_York')
NOW = datetime(2026,11,24,12,tzinfo=ET)
def score(sid, game, date, player='DON'):
    return {'id':str(sid),'name':player,'game':str(game),'gameName':'Game '+str(game),'score':100,'date':date}
def ledger():
    return {'schema_version':1,'awards':[],'verified_plays':[]}
def run(rows, l=None):
    return evaluate(rows, l if l is not None else ledger(), NOW, trusted_approved_feed=True)

class Secrets(unittest.TestCase):
    def test_five_distinct_games_same_day(self):
        rows=[score(i,i,'2026-11-21T13:00:00-05:00') for i in range(5)]
        out, awards=run(rows)
        self.assertEqual([a['type'] for a in awards],['secret_high_five'])
        out2, again=run(rows,out)
        self.assertEqual(again,[])
        self.assertEqual(out,out2)
    def test_duplicate_game_not_counted(self):
        _,awards=run([score(i,1,'2026-11-21T13:00:00-05:00') for i in range(5)])
        self.assertEqual(awards,[])
    def test_eastern_midnight_and_night_owl(self):
        rows=[score(1,1,'2026-11-22T00:00:00-05:00'),score(2,2,'2026-11-22T02:59:59-05:00'),score(3,3,'2026-11-22T03:00:00-05:00')]
        _,awards=run(rows)
        self.assertEqual([a['type'] for a in awards],['secret_night_owl'])
    def test_central_timezone_conversion(self):
        _,awards=run([score(1,1,'11/22/2026 12:30:00 AM')])
        self.assertEqual(len(awards),1) # 1:30 AM Eastern
    def test_rolling_seven_days(self):
        rows=[score(i,i,'2026-11-%02dT12:00:00-05:00'%(20+i//2)) for i in range(10)]
        _,awards=run(rows)
        self.assertEqual([a['type'] for a in awards],['secret_arcade_hopper'])
    def test_eight_day_gap_fails(self):
        rows=[score(i,i,'2026-11-%02dT12:00:00-05:00'%(20+i)) for i in range(8)]
        rows += [score(20,20,'2026-11-27T12:00:00-05:00'),score(21,21,'2026-11-27T12:00:00-05:00')]
        _,awards=run(rows)
        self.assertEqual(awards,[])
    def test_cutover_and_future_rejected(self):
        _,awards=run([score(1,1,'2026-11-19T01:00:00-05:00'),score(2,2,'2026-12-01T01:00:00-05:00')])
        self.assertEqual(awards,[])
    def test_fail_closed_and_immutability(self):
        l=ledger(); old=copy.deepcopy(l)
        with self.assertRaises(ValueError):
            evaluate([],l,NOW)
        out,awards=run([score(1,1,'2026-11-22T01:00:00-05:00')],l)
        self.assertEqual(l,old)
        self.assertEqual(len(out['awards']),1)
    def test_invalid_score_and_duplicate_id(self):
        rows=[score(1,1,'2026-11-22T01:00:00-05:00')]
        rows[0]['score']=-1
        _,awards=run(rows)
        self.assertEqual(awards,[])
    def test_separate_players(self):
        _,awards=run([score(1,1,'2026-11-22T01:00:00-05:00'),score(2,2,'2026-11-22T01:00:00-05:00','RDG')])
        self.assertEqual(len(awards),2)

if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Regression coverage for read-only unified achievement history."""
import copy
import unittest
from build_unified_achievement_history import build, consecutive_streak

def initial():
    daily={'days':[{'date':'2026-11-16','game_id':'1','game':'Game A'},
                   {'date':'2026-11-17','game_id':'2','game':'Game B'}]}
    thurs={'weeks':{'2026-11-05':{'game_id':'77','game':'Setup'},
                   '2026-11-12':{'game_id':'3','game':'Bosconian'}}}
    winners={'weeks':[{'week':'2026-11-12','game_id':'3','game':'Bosconian',
                       'status':'final','winner':{'player':'RDG','score':63450}}]}
    ledger={'schema_version':1,'awards':[{
        'id':'thursday_champion:2026-11-12','type':'thursday_champion',
        'date':'2026-11-12','player':'RDG','game':'Bosconian',
        'game_id':'3','score_id':'384380'}],'verified_plays':[]}
    candidates={'candidates':[{'kind':'thursday','date':'2026-11-12',
                    'game_id':'3','player':'DON','score_id':'384377','best_score':45110},
                    {'kind':'thursday','date':'2026-11-12',
                    'game_id':'3','player':'RDG','score_id':'384380','best_score':63450}]}
    return daily,{},thurs,winners,{},ledger,candidates

class HistoryTest(unittest.TestCase):
    def test_launch_history_but_no_early_setup_week(self):
        data=build(*initial())
        keys={e['event_key'] for e in data['events']}
        self.assertEqual(keys,{'daily:2026-11-16','daily:2026-11-17','thursday:2026-11-12'})
        self.assertEqual(data['players']['RDG']['championships']['thursday'],1)
        self.assertEqual(data['players']['RDG']['participation']['thursday'],1)
        bos=next(x for x in data['events'] if x['event_key']=='thursday:2026-11-12')
        self.assertEqual(bos['champions'],['RDG'])
        self.assertEqual(bos['participants'],['RDG'])
        self.assertEqual(bos['verified_results'][0]['role'],'champion')
        self.assertEqual(bos['verified_results'][0]['score_id'],'384380')
        self.assertEqual([c['player'] for c in bos['unverified_candidates']],['DON'])
        self.assertNotIn('DON',data['players'])
    def test_readonly_and_never_create_awards_from_candidates(self):
        args=initial()
        snapshot=copy.deepcopy(args)
        build(*args)
        self.assertEqual(args,snapshot)
    def test_verified_daily_distinct_event_days(self):
        args=list(initial())
        args[5]['verified_plays']=[
            {'kind':'daily','date':'2026-11-16','game_id':'1','player':'DON'},
            {'kind':'daily','date':'2026-11-16','game_id':'1','player':'DON'},
            {'kind':'daily','date':'2026-11-17','game_id':'2','player':'DON'}]
        data=build(*args)
        self.assertEqual(data['players']['DON']['participation']['daily'],2)
        self.assertEqual(data['players']['DON']['longest_verified_streaks']['daily'],2)
    def test_no_monthly_game_leak_before_public_reveal(self):
        args=list(initial())
        args[4]={'status':'not_launched','month':'2026-12','game_id':'SECRET'}
        data=build(*args)
        self.assertNotIn('SECRET',str(data))
        self.assertFalse(any(e['kind']=='monthly' for e in data['events']))
    def test_monthly_published_game_event(self):
        args=list(initial())
        args[4]={'status':'provisional','month':'2026-12','game_id':'10','game':'Revealed'}
        data=build(*args)
        self.assertTrue(any(e['event_key']=='monthly:2026-12-01' for e in data['events']))
    def test_conflicting_archive_fails_closed(self):
        args=list(initial())
        args[1]={'days':[{'date':'2026-11-16','game_id':'WRONG'}]}
        with self.assertRaises(ValueError):build(*args)
    def test_thursday_streak_requires_adjacent_weeks(self):
        self.assertEqual(consecutive_streak({'2026-11-12','2026-11-26'},'thursday',
            ['2026-11-12','2026-11-19','2026-11-26']),1)

if __name__=='__main__':unittest.main()

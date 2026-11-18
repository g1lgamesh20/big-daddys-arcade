#!/usr/bin/env python3
"""Generous approval-window policy: no old pending-score timestamp inference."""
import copy
import unittest
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from generous_approval_credits import process,approval_time,capture_daily_baselines,scheduled,capture_monthly_reveals

NY=ZoneInfo('America/New_York')
def at(s):return datetime.fromisoformat(s).replace(tzinfo=NY)
def row(sid,player,score,game,approved):
    return {'id':sid,'name':player,'score':score,'game':game,'date':approved}
def ledger():return {'schema_version':1,'awards':[],'verified_plays':[]}
def daily(date,game):
    return {'days':[{'date':date,'game_id':game,'game':'A game'}]}

class GenerousApprovalTests(unittest.TestCase):
    def scan(self,rows,days=None,thurs=None,monthly=None,stored=None,now=None,enabled=True,baselines=None,archive=None):
        return process(rows,days or {'days':[]},{'days':[]},
            thurs or {'weeks':{}},monthly or {},stored or ledger(),
            now or at('2026-11-21T09:00:00'),enabled=enabled,baselines=baselines,monthly_archive=archive)
    def test_naive_iscored_date_assumed_central_for_window(self):
        value=approval_time('2026-11-19 00:30:00')
        self.assertEqual(value.isoformat(),'2026-11-19T01:30:00-05:00')
    def test_late_approval_gets_daily_credit_not_champion_without_baseline(self):
        rows=[row('A','DON',900,'101601','2026-11-19 10:00:00')]
        out,report,changed=self.scan(rows,days=daily('2026-11-18','101601'))
        self.assertTrue(changed)
        self.assertEqual(len(out['verified_plays']),1)
        self.assertEqual(out['verified_plays'][0]['date'],'2026-11-18')
        self.assertEqual(out['awards'],[])
        self.assertEqual(report['new_championships'],[])
    def test_excessively_late_approval_is_not_credited(self):
        out,report,_=self.scan(
          [row('B','DON',900,'101601','2026-11-20 02:00:00')],
          days=daily('2026-11-18','101601'))
        self.assertEqual(report['new_participation_credits'],0)
        self.assertEqual(out,ledger())
    def test_wrong_featured_game_and_pre_event_approval_excluded(self):
        rows=[row('C','DON',200,'OTHER','2026-11-18 19:00:00'),
              row('D','DON',500,'101601','2026-11-17 20:00:00')]
        _,report,_=self.scan(rows,days=daily('2026-11-18','101601'))
        self.assertEqual(report['new_participation_credits'],0)
    def test_same_player_multiple_scores_only_one_credit_best_score(self):
        rows=[row('11','DON',300,'101601','2026-11-18 11:00:00'),
              row('12','DON',700,'101601','2026-11-18 13:00:00')]
        out,report,_=self.scan(rows,days=daily('2026-11-18','101601'))
        self.assertEqual(report['new_participation_credits'],1)
        self.assertEqual(out['verified_plays'][0]['score'],700)
    def test_thursday_champion_only_after_grace_window(self):
        th={'weeks':{'2026-11-19':{'game_id':'77','game':'Test Game'}}}
        rows=[row('X','DON',2000,'77','2026-11-19 14:00:00'),
              row('Y','RDG',1000,'77','2026-11-19 20:00:00')]
        before,_,_=self.scan(rows,thurs=th,now=at('2026-11-20T14:00:00'))
        self.assertEqual(before['awards'],[])
        after,report,_=self.scan(rows,thurs=th,now=at('2026-11-21T09:00:00'))
        self.assertEqual(report['new_championships'][0]['player'],'DON')
        self.assertEqual(after['awards'][0]['type'],'thursday_champion')
        self.assertEqual(len(after['verified_plays']),2)
    def test_existing_champion_and_verified_participants_unchanged(self):
        state=ledger()
        state['awards']=[{'id':'thursday_champion:2026-11-12',
          'type':'thursday_champion','date':'2026-11-12','player':'RDG',
          'event_key':'thursday:2026-11-12:112913:RDG'}]
        state['verified_plays']=[{'kind':'thursday','date':'2026-11-12',
          'player':'DON','event_key':'thursday:2026-11-12:112913:DON'}]
        original=copy.deepcopy(state)
        rows=[row('384380','RDG',63450,'112913','2026-11-12 21:01:29'),
              row('384377','DON',45110,'112913','2026-11-12 19:00:46')]
        out,report,changed=self.scan(rows,thurs={'weeks':{'2026-11-12':{
          'game_id':'112913','game':'Bosconian'}}},stored=state)
        self.assertFalse(changed)
        self.assertEqual(report['new_participation_credits'],0)
        self.assertEqual(out,original)
    def test_daily_champion_only_if_locked_score_beaten(self):
        rows=[row('1','RDG',3000,'101601','2026-11-18 14:00:00'),
              row('2','DON',1900,'101601','2026-11-18 15:00:00')]
        baselines={'2026-11-18':{'game_id':'101601','starting_champion_score':2000}}
        out,report,_=self.scan(rows,days=daily('2026-11-18','101601'),baselines=baselines)
        self.assertEqual([x['player'] for x in report['new_championships']],['RDG'])
        self.assertEqual(len([a for a in out['awards'] if a['type']=='daily_champion']),1)
    def test_two_players_beating_daily_baseline_both_get_gold_trophies(self):
        rows=[row('A','RDG',3000,'101601','2026-11-18 12:00:00'),
              row('B','DON',2200,'101601','2026-11-19 07:00:00'),
              row('C','DAY',1800,'101601','2026-11-18 15:00:00')]
        baselines={'2026-11-18':{'game_id':'101601','starting_champion_score':2000}}
        out,report,changed=self.scan(rows,days=daily('2026-11-18','101601'),
            baselines=baselines)
        winners=[a for a in out['awards'] if a['type']=='daily_champion']
        self.assertEqual({a['player'] for a in winners},{'DON','RDG'})
        self.assertEqual(len(out['verified_plays']),3)
        self.assertTrue(all(a['gold_level'] is True and
                            a['starting_champion_score']==2000 for a in winners))
        self.assertTrue(all(a['win_rule']=='strictly_greater_than_locked_starting_champion_score'
                            for a in winners))
        self.assertEqual(len(report['new_championships']),2)
        self.assertTrue(changed)
    def test_daily_gold_remembers_pre_event_snapshot_provenance(self):
        rows=[row('A','DON',2500,'101601','2026-11-18 12:00:00')]
        baselines={'2026-11-18':{'game_id':'101601','starting_champion_score':2000,
            'observed_at':'2026-11-17T23:52:00-05:00',
            'evidence':'pre_start_approved_iscored_score_snapshot'}}
        out,_,_=self.scan(rows,days=daily('2026-11-18','101601'),
            baselines=baselines)
        award=next(a for a in out['awards'] if a['type']=='daily_champion')
        self.assertEqual(award['starting_champion_observed_at'],
                         '2026-11-17T23:52:00-05:00')
        self.assertEqual(award['starting_champion_evidence'],
                         'pre_start_approved_iscored_score_snapshot')
    def test_daily_late_second_winner_not_blocked_by_existing_gold_winner(self):
        rows=[row('A','RDG',3000,'101601','2026-11-18 12:00:00'),
              row('B','DON',2200,'101601','2026-11-19 07:00:00')]
        baselines={'2026-11-18':{'game_id':'101601','starting_champion_score':2000}}
        existing=ledger()
        existing['awards'].append({'id':'daily_champion:2026-11-18:RDG',
            'event_key':'daily:2026-11-18:101601:RDG','type':'daily_champion',
            'name':'Daily Champion','date':'2026-11-18','player':'RDG',
            'game':'A game','game_id':'101601','score':3000,'score_id':'A'})
        out,report,_=self.scan(rows,days=daily('2026-11-18','101601'),
            baselines=baselines,stored=existing)
        self.assertEqual(len([a for a in out['awards'] if a['type']=='daily_champion']),2)
        self.assertEqual([a['player'] for a in report['new_championships']],['DON'])
    def test_daily_repeated_scan_never_duplicates_winner_trophies(self):
        rows=[row('A','RDG',3000,'101601','2026-11-18 12:00:00'),
              row('B','DON',2200,'101601','2026-11-19 07:00:00')]
        baselines={'2026-11-18':{'game_id':'101601','starting_champion_score':2000}}
        first,_,_=self.scan(rows,days=daily('2026-11-18','101601'),
             baselines=baselines)
        second,report,changed=self.scan(rows,days=daily('2026-11-18','101601'),
             baselines=baselines,stored=first)
        self.assertFalse(changed)
        self.assertEqual(len([a for a in second['awards'] if a['type']=='daily_champion']),2)
        self.assertEqual(report['new_championships'],[])
    def test_equal_starting_target_is_not_a_daily_victory(self):
        rows=[row('A','DON',2000,'101601','2026-11-18 12:00:00')]
        baselines={'2026-11-18':{'game_id':'101601','starting_champion_score':2000}}
        out,_,_=self.scan(rows,days=daily('2026-11-18','101601'),
            baselines=baselines)
        self.assertEqual(out['awards'],[])
        self.assertEqual(len(out['verified_plays']),1)
    def test_no_locked_starting_target_no_daily_champion(self):
        rows=[row('A','DON',5000,'101601','2026-11-18 12:00:00')]
        out,_,_=self.scan(rows,days=daily('2026-11-18','101601'))
        self.assertEqual(out['awards'],[])
        self.assertEqual(len(out['verified_plays']),1)
    def test_wait_until_full_daily_approval_grace_before_gold_trophies(self):
        rows=[row('A','DON',5000,'101601','2026-11-18 15:00:00')]
        baselines={'2026-11-18':{'game_id':'101601','starting_champion_score':2000}}
        before,_,_=self.scan(rows,days=daily('2026-11-18','101601'),
            now=at('2026-11-19T14:00:00'),baselines=baselines)
        self.assertEqual(before['awards'],[])
        after,_,_=self.scan(rows,days=daily('2026-11-18','101601'),
            now=at('2026-11-20T00:01:00'),baselines=baselines)
        self.assertEqual(len(after['awards']),1)
    def test_monthly_not_revealed_no_game_leaks(self):
        rows=[row('P','DON',1000,'HIDDEN','2026-12-20 12:00:00')]
        out,report,_=self.scan(rows,monthly={'month':'2026-12','game_id':'HIDDEN',
          'status':'not_launched'},now=at('2027-01-05T12:00:00'))
        self.assertEqual(out,ledger())
        self.assertNotIn('HIDDEN',str(report))
    def test_revealed_monthly_winner_after_end_plus_grace(self):
        rows=[row('1','DON',500,'99','2026-12-20 13:00:00'),
              row('2','RDG',700,'99','2026-12-22 13:00:00')]
        live={'status':'provisional','month':'2026-12','game_id':'99','game':'Test'}
        out,report,_=self.scan(rows,monthly=live,now=at('2027-01-02T12:00:00'))
        self.assertEqual(report['new_championships'][0]['player'],'RDG')
        self.assertEqual(out['awards'][0]['event_month'],'2026-12')
        self.assertEqual(len(out['verified_plays']),2)
    def test_monthly_podium_three_positions_and_75_percent_benchmark(self):
        public={'status':'provisional','month':'2026-12','game_id':'99',
                'game':'Robotron','starting_record':1000,'benchmark':750}
        rows=[row('1','DON',1000,'99','2026-12-08 12:00:00'),
              row('2','RDG',900,'99','2026-12-09 12:00:00'),
              row('3','SPC',800,'99','2026-12-10 12:00:00'),
              row('4','DAY',700,'99','2026-12-11 12:00:00')]
        out,report,_=self.scan(rows,monthly=public,now=at('2027-01-02T08:00:00'))
        podium={a['player']:a['rank'] for a in out['awards']
                if a['type'].startswith('gotm_podium_')}
        self.assertEqual(podium,{'DON':1,'RDG':2,'SPC':3})
        above={a['player'] for a in out['awards'] if a['type']=='gotm_beat_average'}
        self.assertEqual(above,{'DON','RDG','SPC'})
        self.assertTrue(all(a['locked_benchmark']==750
                            for a in out['awards'] if a['type']=='gotm_beat_average'))
        self.assertEqual(len(out['verified_plays']),4)
        self.assertEqual({a['player'] for a in out['awards'] if a['type']=='gotm_champion'},{'DON'})
        self.assertEqual(len(report['new_monthly_trophies']),6)
    def test_monthly_podium_ties_use_1_1_3(self):
        public={'status':'provisional','month':'2026-12','game_id':'99','game':'Robotron',
                'starting_record':1000,'benchmark':750}
        rows=[row('1','DON',1000,'99','2026-12-08 12:00:00'),
              row('2','RDG',1000,'99','2026-12-09 12:00:00'),
              row('3','SPC',900,'99','2026-12-10 12:00:00')]
        out,_,_=self.scan(rows,monthly=public,now=at('2027-01-02T08:00:00'))
        podium={a['player']:a['rank'] for a in out['awards']
                if a['type'].startswith('gotm_podium_')}
        self.assertEqual(podium,{'DON':1,'RDG':1,'SPC':3})
    def test_monthly_benchmark_equal_does_not_beat_average(self):
        public={'status':'provisional','month':'2026-12','game_id':'99','game':'Robotron',
                'starting_record':1000,'benchmark':750}
        out,_,_=self.scan([row('1','DON',750,'99','2026-12-08 12:00:00')],
                           monthly=public,now=at('2027-01-02T08:00:00'))
        self.assertFalse(any(a['type']=='gotm_beat_average' for a in out['awards']))
        self.assertTrue(any(a['type']=='gotm_podium_1' for a in out['awards']))
    def test_no_average_trophy_without_valid_locked_benchmark(self):
        public={'status':'provisional','month':'2026-12','game_id':'99','game':'Robotron'}
        out,_,_=self.scan([row('1','DON',5000,'99','2026-12-08 12:00:00')],
                           monthly=public,now=at('2027-01-02T08:00:00'))
        self.assertFalse(any(a['type']=='gotm_beat_average' for a in out['awards']))
    def test_monthly_24h_grace_and_idempotent_trophies(self):
        public={'status':'provisional','month':'2026-12','game_id':'99','game':'Robotron',
                'starting_record':1000,'benchmark':750}
        rows=[row('1','DON',900,'99','2026-12-20 12:00:00'),
              row('2','RDG',800,'99','2027-01-01 12:00:00')]
        before,_,_=self.scan(rows,monthly=public,now=at('2027-01-01T23:00:00'))
        self.assertFalse(before['awards'])
        after,_,_=self.scan(rows,monthly=public,now=at('2027-01-02T08:00:00'))
        self.assertEqual(len([a for a in after['awards'] if a['type'].startswith('gotm_')]),5)
        again,report,changed=self.scan(rows,monthly=public,
                   stored=after,now=at('2027-01-03T09:00:00'))
        self.assertFalse(changed)
        self.assertEqual(report['new_monthly_trophies'],[])
        self.assertEqual(again,after)
    def test_revealed_benchmark_archived_across_next_month(self):
        first={'status':'provisional','month':'2026-12','game_id':'99','game':'Robotron',
               'starting_record':1000,'benchmark':750}
        archive=capture_monthly_reveals(first,{'schema_version':1,'months':{}})
        self.assertEqual(archive['months']['2026-12']['benchmark'],750)
        january={'status':'provisional','month':'2027-01','game_id':'100','game':'New Game',
                 'starting_record':2000,'benchmark':1500}
        new_archive=capture_monthly_reveals(january,archive)
        rows=[row('1','DON',1000,'99','2026-12-20 12:00:00')]
        out,_,_=self.scan(rows,monthly=january,archive=new_archive,
                          now=at('2027-01-02T08:00:00'))
        self.assertEqual([a['type'] for a in out['awards'] if a['type']=='gotm_beat_average'],
                         ['gotm_beat_average'])
        self.assertEqual(out['awards'][0]['event_month'],'2026-12')
        with self.assertRaises(ValueError):
            capture_monthly_reveals({**first,'benchmark':749},archive)
    def test_no_early_monthly_game_reveal_or_trophies(self):
        private={'status':'not_launched','month':'2026-12','game_id':'SECRET',
                 'starting_record':1000,'benchmark':750}
        out,report,_=self.scan([row('1','DON',900,'SECRET','2026-12-20 12:00:00')],
            monthly=private,now=at('2027-01-02T08:00:00'))
        self.assertEqual(out,ledger())
        self.assertNotIn('SECRET',str(report))
    def test_monthly_after_new_month_reveal_uses_archived_old_game(self):
        revealed={'status':'provisional','month':'2026-12','game_id':'99','game':'Old Game'}
        archive=capture_monthly_reveals(revealed,{'schema_version':1,'months':{}})
        january={'status':'provisional','month':'2027-01','game_id':'100','game':'New Game'}
        archived=capture_monthly_reveals(january,archive)
        rows=[row('z','DON',1000,'99','2026-12-28 13:00:00')]
        out,report,_=self.scan(rows,monthly=january,archive=archived,
                               now=at('2027-01-02T12:00:00'))
        self.assertEqual(len(out['verified_plays']),1)
        self.assertEqual(out['verified_plays'][0]['event_month'],'2026-12')
        self.assertEqual(report['new_championships'][0]['date'],'2026-12-01')
    def test_revealed_monthly_archive_immutable(self):
        base=capture_monthly_reveals({'status':'provisional','month':'2026-12',
                   'game_id':'99','game':'Game'}, {'schema_version':1,'months':{}})
        with self.assertRaises(ValueError):
            capture_monthly_reveals({'status':'provisional','month':'2026-12',
                'game_id':'100','game':'Wrong Game'},base)
    def test_unrevealed_game_never_enters_monthly_archive(self):
        archive=capture_monthly_reveals({'status':'not_launched','month':'2026-12',
                   'game_id':'SECRET'}, {'schema_version':1,'months':{}})
        self.assertNotIn('SECRET',str(archive))
    def test_preview_writes_nothing(self):
        state=ledger()
        snapshot=copy.deepcopy(state)
        out,report,changed=self.scan(
            [row('1','DON',900,'101601','2026-11-18 13:00:00')],
            days=daily('2026-11-18','101601'),stored=state,enabled=False)
        self.assertEqual(out,snapshot)
        self.assertFalse(changed)
        self.assertEqual(state,snapshot)
        self.assertEqual(report['new_participation_credits'],1)
    def test_baseline_only_collected_before_start(self):
        rows=[row('old','RDG',1500,'101601','2026-11-17 13:00:00')]
        original={}
        snap=capture_daily_baselines(rows,{'days':[]},daily('2026-11-18','101601'),
            original,at('2026-11-17T22:00:00'))
        self.assertEqual(snap['2026-11-18']['starting_champion_score'],1500)
        frozen=capture_daily_baselines([row('new','RDG',9900,'101601','2026-11-18 13:00:00')],
            {'days':[]},daily('2026-11-18','101601'),snap,
            at('2026-11-18T16:00:00'))
        self.assertEqual(frozen,snap)

if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Regression tests: Golden Encore requires a NEW improvement over an OLD Gold."""
import copy
import unittest
from datetime import datetime, timezone
from golden_encore import evaluate, snapshot

NOW = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)
def row(sid, player, game, value):
    return {'id': sid, 'name': player, 'game': game, 'gameName': 'Robotron',
            'score': value}
def empty():
    return {'schema_version': 1, 'awards': [], 'verified_plays': []}
def state(rows):
    return {'schema_version': 1, 'gold_by_game': snapshot(rows), 'improvements': []}

class GoldenEncoreTests(unittest.TestCase):
    def test_first_load_is_quiet(self):
        output, ledger, events = evaluate([row('1','DON','A',100)],None,set(),empty(),NOW)
        self.assertEqual(events,[])
        self.assertEqual(ledger['awards'],[])
        self.assertEqual(output['gold_by_game']['A']['score'],100)
    def test_improve_existing_gold_unlocks_once(self):
        old=state([row('1','DON','A',100),row('2','RDG','A',90)])
        feed=[row('1','DON','A',100),row('2','RDG','A',90),row('3','DON','A',150)]
        updated, ledger, events=evaluate(feed,old,{'1','2'},empty(),NOW)
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['previous_gold_score'],100)
        self.assertEqual(ledger['awards'][0]['name'],'Golden Encore')
        again, next_ledger, new_events=evaluate(feed,updated,{'1','2','3'},ledger,NOW)
        self.assertEqual(new_events,[])
        self.assertEqual(len(next_ledger['awards']),1)
        self.assertEqual(again['improvements'],updated['improvements'])
    def test_new_gold_from_silver_not_eligible(self):
        old=state([row('1','DON','A',100),row('2','RDG','A',90)])
        _, ledger, events=evaluate([row('1','DON','A',100),
          row('3','RDG','A',140)],old,{'1','2'},empty(),NOW)
        self.assertEqual(events,[])
        self.assertEqual(ledger['awards'],[])
    def test_tie_does_not_unlock(self):
        old=state([row('1','DON','A',100)])
        _, ledger, events=evaluate([row('1','DON','A',100),
          row('3','DON','A',100)],old,{'1'},empty(),NOW)
        self.assertEqual(events,[])
        self.assertEqual(ledger['awards'],[])
    def test_existing_score_id_does_not_backfill(self):
        old=state([row('1','DON','A',100)])
        _, ledger, events=evaluate([row('3','DON','A',150)],old,{'1','3'},empty(),NOW)
        self.assertEqual(events,[])
        self.assertEqual(ledger['awards'],[])
    def test_current_best_other_player_prevents_false_award(self):
        old=state([row('1','DON','A',100)])
        _, ledger, events=evaluate([row('3','DON','A',150),
            row('4','RDG','A',200)],old,{'1'},empty(),NOW)
        self.assertEqual(events,[])
        self.assertEqual(ledger['awards'],[])
    def test_tied_gold_holder_can_earn(self):
        old=state([row('1','DON','A',100),row('2','RDG','A',100)])
        _, ledger, events=evaluate([row('3','RDG','A',150)],
                                  old,{'1','2'},empty(),NOW)
        self.assertEqual(len(events),1)
        self.assertEqual(ledger['awards'][0]['player'],'RDG')
    def test_five_and_ten_milestones_no_duplicates(self):
        previous=state([row('1','DON','A',100)])
        ledger=empty()
        for n in range(1,11):
            sid=str(100+n)
            feed=[row(sid,'DON','A',100+n)]
            previous, ledger, events=evaluate(feed,previous,{str(x) for x in range(1,101)},
                                               ledger,NOW)
            self.assertEqual(len(events),1)
        self.assertEqual([a['name'] for a in sorted(ledger['awards'],
                              key=lambda a:a['milestone'])],
                         ['Golden Encore','Gold Rush','Untouchable'])
        self.assertEqual(len(previous['improvements']),10)
        self.assertEqual(len(set(a['id'] for a in ledger['awards'])),3)
    def test_existing_trophies_unchanged(self):
        base=empty()
        base['awards'].append({'id':'thursday_champion:2026-11-12',
                              'player':'RDG','date':'2026-11-12'})
        before=copy.deepcopy(base)
        old=state([row('1','DON','A',100)])
        _, updated, events=evaluate([row('3','DON','A',150)],old,{'1'},base,NOW)
        self.assertEqual(base,before)
        self.assertEqual(updated['awards'][0],before['awards'][0])
        self.assertEqual(len(events),1)
    def test_missing_game_reappearance_does_not_award(self):
        old=state([row('1','DON','A',100)])
        missing,ledger,events=evaluate([],old,{'1'},empty(),NOW)
        self.assertEqual(events,[])
        self.assertIn('A',missing['missing_games'])
        recovered,ledger,events=evaluate([row('2','DON','A',150)],missing,{'1'},ledger,NOW)
        self.assertEqual(events,[])
        self.assertEqual(ledger['awards'],[])
        self.assertNotIn('A',recovered['missing_games'])
        _,ledger,events=evaluate([row('3','DON','A',160)],recovered,{'1','2'},ledger,NOW)
        self.assertEqual(len(events),1)
    def test_lower_gold_snapshot_never_awards(self):
        old=state([row('1','DON','A',200)])
        lowered,ledger,events=evaluate([row('2','DON','A',100)],old,{'1'},empty(),NOW)
        self.assertEqual(events,[])
        self.assertEqual(lowered['gold_by_game']['A']['score'],100)
        _,ledger,events=evaluate([row('3','DON','A',150)],lowered,{'1','2'},ledger,NOW)
        self.assertEqual(len(events),1)
    def test_missing_one_game_does_not_block_another(self):
        old=state([row('1','DON','A',100),row('2','RDG','B',100)])
        _,ledger,events=evaluate([row('3','RDG','B',150)],old,{'1','2'},empty(),NOW)
        self.assertEqual(len(events),1)
        self.assertEqual(ledger['awards'][0]['player'],'RDG')
    def test_bad_state_refuses_to_start_over(self):
        with self.assertRaises(ValueError):
            evaluate([],{'schema_version':1,'improvements':[]},set(),empty(),NOW)

if __name__=='__main__':
    unittest.main()

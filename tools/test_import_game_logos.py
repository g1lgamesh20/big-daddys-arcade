#!/usr/bin/env python3
"""Regression tests for secure, additive iScored artwork metadata imports."""
import unittest
from import_game_logos import merge, rows_from

class LogoImportTests(unittest.TestCase):
    def test_community_and_custom_art(self):
        m={'49994':'/images/games/game49994'}
        rows=[
            {'RoomID':1118,'GameID':49994,'GameLogo':'/images/games/game49994'},
            {'RoomID':1118,'GameID':101601,'GameLogo':'/community/images/games/game2781'},
        ]
        out, report=merge(m,rows)
        self.assertEqual(out['101601'],'/community/images/games/game2781')
        self.assertEqual(report['changed'],1)
        self.assertEqual(report['total_mapped'],2)

    def test_partial_export_keeps_existing(self):
        out,_=merge({'49994':'/images/games/game49994'},
            [{'GameID':101601,'GameLogo':'/community/images/games/game2781'}])
        self.assertIn('49994',out)

    def test_invalid_or_foreign_entries_skipped(self):
        out,report=merge({},[
            {'GameID':10,'GameLogo':'https://evil.test/bad.png'},
            {'GameID':11,'GameLogo':'/images/games/game11?token=x'},
            {'GameID':12,'GameLogo':'/community/images/games/game12','RoomID':9999},
            {'GameID':13,'GameLogo':'/images/games/game13','RoomID':1118},
        ])
        self.assertEqual(out,{'13':'/images/games/game13'})
        self.assertEqual(report['other_room'],1)
        self.assertEqual(report['invalid'],2)

    def test_missing_logo_doesnt_overwrite(self):
        old={'49994':'/images/games/game49994'}
        out,report=merge(old,[{'GameID':49994,'GameLogo':None},
                                {'GameID':101601,'GameLogo':'/community/images/games/game2781'}])
        self.assertEqual(out['49994'],old['49994'])
        self.assertEqual(report['missing_logo'],1)

    def test_conflicting_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            merge({},[{'GameID':1,'GameLogo':'/images/games/game1'},
                      {'GameID':1,'GameLogo':'/images/games/game2'}])

    def test_no_valid_rows_rejected(self):
        with self.assertRaisesRegex(ValueError,'No valid'):
            merge({},[{'GameID':1,'GameLogo':None}])

    def test_common_wrappers(self):
        for key in ('games','Games','rows','data','result'):
            self.assertEqual(rows_from({key:[{'GameID':1}]}),[{'GameID':1}])
        self.assertEqual(rows_from({'GameID':1}),[{'GameID':1}])

if __name__=='__main__':
    unittest.main()

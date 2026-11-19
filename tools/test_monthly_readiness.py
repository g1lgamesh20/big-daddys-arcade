#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
sys.path.insert(0,str(Path(__file__).resolve().parent))
from monthly_private_selection import seal
from monthly_readiness import check

KEY=bytes(range(32))
def at(s):return datetime.fromisoformat(s).replace(tzinfo=ZoneInfo('America/New_York'))
def fixture(method='random', game='99'):
  packet=seal(AESGCM(KEY),{'month':'2026-12','game_id':game,'method':method})
  return {'version':1,'selections':{'2026-12':packet}}
CAT={'games':{'99':'Mystery Arcade Game'}}
POOL={'excluded_game_ids':[]}
ROWS=[{'game':'99','score':1000,'date':'2026-11-12T12:00:00-05:00','name':'AAA'}]
class ReadinessTests(unittest.TestCase):
 def test_ready_without_reveal(self):
  self.assertEqual(check('2026-12',fixture(),CAT,POOL,KEY,ROWS,at('2026-11-25T12:00:00')),'ready')
 def test_missing_history_blocks(self):
  with self.assertRaisesRegex(ValueError,'no usable pre-month'):
   check('2026-12',fixture(),CAT,POOL,KEY,[],at('2026-11-25T12:00:00'))
 def test_selected_game_does_not_leak_in_exception(self):
  with self.assertRaisesRegex(ValueError,'catalog'):
   check('2026-12',fixture(game='SECRET-FAKE'),CAT,POOL,KEY,ROWS,at('2026-11-25T12:00:00'))
 def test_random_exclusion_blocks_but_operator_override_allowed(self):
  excluded={'excluded_game_ids':['99']}
  with self.assertRaisesRegex(ValueError,'excluded'):
   check('2026-12',fixture(),CAT,excluded,KEY,ROWS,at('2026-11-25T12:00:00'))
  self.assertEqual(check('2026-12',fixture(method='operator'),CAT,excluded,KEY,ROWS,at('2026-11-25T12:00:00')),'ready')
 def test_no_post_midnight_retroactive_lock_claim(self):
  with self.assertRaisesRegex(ValueError,'started'):
   check('2026-12',fixture(),CAT,POOL,KEY,ROWS,at('2026-12-01T00:01:00'))
 def test_valid_locked_benchmark(self):
  payload={'month':'2026-12','game_id':'99','benchmark_lock':{
   'month_start':'2026-12-01T00:00:00-05:00','starting_record':1000,'benchmark':750}}
  packet={'version':1,'selections':{'2026-12':seal(AESGCM(KEY),payload)}}
  self.assertEqual(check('2026-12',packet,CAT,POOL,KEY,ROWS,at('2026-12-01T09:00:00')),'locked')
 def test_tampered_lock_rejected(self):
  payload={'month':'2026-12','game_id':'99','benchmark_lock':{
   'month_start':'2026-12-01T00:00:00-05:00','starting_record':1000,'benchmark':749}}
  packet={'version':1,'selections':{'2026-12':seal(AESGCM(KEY),payload)}}
  with self.assertRaisesRegex(ValueError,'arithmetic'):
   check('2026-12',packet,CAT,POOL,KEY,ROWS,at('2026-12-01T09:00:00'))
if __name__=='__main__':unittest.main()

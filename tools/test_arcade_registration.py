#!/usr/bin/env python3
import base64, hashlib, re, unittest
from datetime import datetime,timezone
from issue_arcade_registration_code import generate

class RegistrationTests(unittest.TestCase):
 def test_code_is_128_bit_random_base32_and_digest_only(self):
  code,statement=generate('don',random_bytes=bytes(range(16)),now=datetime(2026,11,19,tzinfo=timezone.utc))
  self.assertRegex(code,r'^[A-Z2-7]{26}$')
  self.assertEqual(base64.b32decode(code+'======'),bytes(range(16)))
  self.assertIn(hashlib.sha256(code.encode()).hexdigest(),statement)
  self.assertNotIn(code,statement)
  self.assertIn("'DON'",statement)
  self.assertIn('2026-11-26',statement)
 def test_reject_invalid_initials(self):
  for value in ['','    ','LONG','D\'N','DON;','don--']:
   with self.assertRaises(ValueError):generate(value)
 def test_reject_weak_code_and_expiry(self):
  with self.assertRaises(ValueError):generate('DON',random_bytes=b'abc')
  with self.assertRaises(ValueError):generate('DON',days=0)
 def test_server_only_contract(self):
  code=open('supabase/functions/arcade-register/index.ts',encoding='utf8').read()
  sql=open('supabase/social-registration.sql',encoding='utf8').read()
  self.assertIn("TURNSTILE_SECRET_KEY",code)
  self.assertIn("arcade_redeem_registration",code)
  self.assertIn("identity_verified",open('tools/social_achievement_rules.py',encoding='utf8').read())
  self.assertIn('revoke all on function public.arcade_redeem_registration',sql)
  self.assertIn('to service_role',sql)

if __name__=='__main__':unittest.main()

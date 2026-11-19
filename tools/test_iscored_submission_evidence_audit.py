#!/usr/bin/env python3
"""No network needed. Never issues medals, results, or pushes."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from iscored_submission_evidence_audit import inspect, classify, paths

class EvidenceAuditTests(unittest.TestCase):
 def test_api_date_is_not_original_submission_proof(self):
  result=inspect({'scores':[{'id':123,'game':'secret','name':'DON','score':5000,'date':'2026-12-31 20:00:00'}]})
  self.assertFalse(result['original_submission_time_verified'])
  self.assertFalse(result['eligible_for_automatic_official_winner_announcement'])
  self.assertIn('date',result['public_field_names'])
  self.assertNotIn('DON',str(result))
  self.assertNotIn('5000',str(result))
  self.assertNotIn('secret',str(result))
 def test_credible_names_are_only_hints_not_authority(self):
  result=inspect({'scores':[{'submitted_at':'2026-12-31T23:59:00-05:00',
                             'approved_at':'2027-01-01T01:00:00-05:00',
                             'approval_status':'approved','name':'RDG'}]})
  self.assertEqual(result['submission_field_candidates_unconfirmed'],1)
  self.assertFalse(result['original_submission_time_verified'])
  self.assertFalse(result['approval_pending_state_verified'])
  self.assertNotIn('RDG',str(result))
  self.assertNotIn('2026-12-31T',str(result))
 def test_nested_metadata_fields_without_values(self):
  fields=paths({'metadata':{'submittedAt':'timestamp','approval':{'status':'approved'}}})
  self.assertIn('metadata.submittedAt',fields)
  self.assertIn('metadata.approval.status',fields)
 def test_no_raw_personal_values(self):
  result=inspect({'scores':[{'player':'PRIVATE HANDLE','photoUrl':'https://example.com/private-photo',
                             'submittedAt':'SECRET TOKEN','id':'PRIVATE ID'}]})
  self.assertNotIn('PRIVATE HANDLE',str(result))
  self.assertNotIn('SECRET TOKEN',str(result))
  self.assertNotIn('PRIVATE ID',str(result))
 def test_malformed_response_blocks(self):
  for obj in (None,[],{}, {'scores':{}}):
   with self.assertRaises(ValueError):inspect(obj)
 def test_unknown_fields_do_not_pass(self):
  self.assertEqual(classify('date'),'ambiguous_or_approval_date')
  self.assertEqual(classify('submitted_at'),'possible_submission_field_UNCONFIRMED')
if __name__=='__main__':unittest.main()

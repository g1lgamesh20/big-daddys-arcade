#!/usr/bin/env python3
"""Offline tests: no iScored network requests, no notifications."""
import io
import json
import unittest
from urllib.error import HTTPError, URLError
from iscored_fetch_retry import read_scores

class Reply:
 status=200
 def __init__(self,data):self.data=data
 def __enter__(self):return io.BytesIO(json.dumps(self.data).encode('utf-8'))
 def __exit__(self,*args):return False

def http(code):
 return HTTPError('https://www.iScored.info/api/test',code,'synthetic error',{},None)

class Tests(unittest.TestCase):
 def test_success_single_request(self):
  calls=[]
  def opener(req,timeout):
   calls.append(timeout);return Reply({'scores':[{'score':42}]})
  self.assertEqual(read_scores('request',opener=opener,sleeper=lambda n:None)['scores'][0]['score'],42)
  self.assertEqual(calls,[25])
 def test_transient_403_retries_then_success(self):
  delays=[];calls=[]
  def opener(req,timeout):
   calls.append(True)
   if len(calls)<3:raise http(403)
   return Reply({'scores':[1]})
  self.assertEqual(read_scores('request',opener=opener,sleeper=delays.append)['scores'],[1])
  self.assertEqual(delays,[2,5]);self.assertEqual(len(calls),3)
 def test_persistent_403_fails_without_feed_mutation(self):
  calls=[]
  def opener(req,timeout):
   calls.append(True);raise http(403)
  with self.assertRaises(HTTPError):
   read_scores('request',opener=opener,sleeper=lambda _:None)
  self.assertEqual(len(calls),3)
 def test_non_retryable_401_fails_immediately(self):
  calls=[]
  def opener(req,timeout):
   calls.append(True);raise http(401)
  with self.assertRaises(HTTPError):
   read_scores('request',opener=opener,sleeper=lambda _:None)
  self.assertEqual(len(calls),1)
 def test_malformed_response_never_retries(self):
  calls=[]
  def opener(req,timeout):
   calls.append(True);return Reply({'unexpected':[]})
  with self.assertRaises(ValueError):
   read_scores('request',opener=opener,sleeper=lambda _:None)
  self.assertEqual(len(calls),1)
 def test_network_error_retries(self):
  calls=[]
  def opener(req,timeout):
   calls.append(True)
   if len(calls)==1:raise URLError('synthetic')
   return Reply({'scores':[]})
  self.assertEqual(read_scores('request',opener=opener,sleeper=lambda _:None)['scores'],[])
  self.assertEqual(len(calls),2)
if __name__=='__main__':unittest.main()

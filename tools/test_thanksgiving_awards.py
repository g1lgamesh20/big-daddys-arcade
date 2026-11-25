#!/usr/bin/env python3
"""Offline tests for the Thanksgiving-only achievement launch."""
import copy
import unittest
from datetime import date, datetime, timezone

from thanksgiving_awards import activate, thanksgiving


class ThanksgivingTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"schema_version": 1, "awards": [{"id": "easter_egg:DON", "player": "DON", "type": "easter_egg"}], "verified_plays": [{"event_key": "daily:old"}]}
        self.now = datetime(2026, 11, 29, 12, 0, tzinfo=timezone.utc)

    def journal(self, rows):
        return {"schema_version": 1, "scores": {str(k): dict(score_id=str(k), name=player, game="50010", gameName="1942", score=100, date=when)
            for k, (player, when) in rows.items()}}

    def test_fourth_thursday_dates(self):
        self.assertEqual(thanksgiving(2026), date(2026, 11, 26))
        self.assertEqual(thanksgiving(2027), date(2027, 11, 25))
        self.assertEqual(thanksgiving(2028), date(2028, 11, 23))

    def test_eastern_midnight_and_late_approval(self):
        j=self.journal({
            1:("DON", "2026-11-26T05:00:00+00:00"), # 00:00 Eastern
            2:("VJG", "2026-11-27T04:59:59+00:00"), # 23:59:59 Eastern
            3:("DAY", "2026-11-27T05:00:00+00:00"), # Friday, not eligible
            4:("SPC", "2026-11-26T04:59:59+00:00"), # Wednesday, not eligible
        })
        original=copy.deepcopy(self.ledger)
        result,awards=activate(j,self.ledger,self.now,enabled=True)
        self.assertEqual({a["player"] for a in awards},{"DON","VJG"})
        self.assertEqual(self.ledger,original)
        self.assertEqual(result["verified_plays"],original["verified_plays"])
        result2,again=activate(j,result,self.now,enabled=True)
        self.assertEqual(again,[])
        self.assertEqual(len(result2["awards"]),len(result["awards"]))

    def test_iscored_naive_server_time_is_central(self):
        # 11:30 PM Central Thanksgiving is already 00:30 Friday Eastern.
        j=self.journal({1:("DON","2026-11-26 23:30:00"),2:("VJG","2026-11-26 22:30:00")})
        _,awards=activate(j,self.ledger,self.now,enabled=True)
        self.assertEqual([a["player"] for a in awards],["VJG"])

    def test_approved_later_still_counts(self):
        _,a=activate(self.journal({88:("DON","2026-11-26T14:00:00-05:00")}),self.ledger,self.now,enabled=True)
        self.assertEqual(a[0]["date"],"2026-11-26")
        self.assertEqual(a[0]["score_id"],"88")

    def test_non_approved_not_in_journal(self):
        _,a=activate(self.journal({}),self.ledger,self.now,enabled=True)
        self.assertEqual(a,[])

    def test_lifetime_after_year_changes(self):
        previous={"schema_version":1,"awards":[{"id":"holiday_thanksgiving:DON","type":"holiday_thanksgiving","player":"DON"}],"verified_plays":[]}
        j=self.journal({1:("DON","2027-11-25T17:00:00-05:00")})
        _,awards=activate(j,previous,datetime(2027,11,26,tzinfo=timezone.utc),enabled=True)
        self.assertEqual(awards,[])

    def test_fails_closed_on_bad_ledger(self):
        with self.assertRaises(ValueError):
            activate(self.journal({}),{"schema_version":1,"awards":[]},self.now,enabled=True)

    def test_off_by_default(self):
        out,a=activate(self.journal({1:("DON","2026-11-26T17:00:00-05:00")}),self.ledger,self.now)
        self.assertEqual(a,[])
        self.assertEqual(out,self.ledger)


if __name__ == "__main__":
    unittest.main()

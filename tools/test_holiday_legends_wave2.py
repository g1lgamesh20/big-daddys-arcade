#!/usr/bin/env python3
"""Offline calendar, score-provenance, repeatability and prank exclusion tests."""
import unittest
from datetime import date,datetime,timezone
from holiday_legends_wave2 import easter,holy_thursday,holiday_on,activate,ALL_HOLIDAYS

def sample(rows):
    return {"schema_version":1,"scores":{
        str(i):{"score_id":str(i),"name":player,"date":when,
                "game":game,"gameName":"Arcade Game","score":100}
        for i,(player,when,game) in enumerate(rows,1)}}

def blank():
    return {"schema_version":1,"awards":[],"verified_plays":[]}

class Wave2Tests(unittest.TestCase):
    def test_easter_and_holy_thursday(self):
        self.assertEqual(easter(2027),date(2027,3,28))
        self.assertEqual(holy_thursday(2027),date(2027,3,25))
        self.assertEqual(easter(2028),date(2028,4,16))
        self.assertEqual(holy_thursday(2028),date(2028,4,13))

    def test_all_ten_holidays(self):
        expected={
            date(2027,2,14):"holiday_valentines",date(2027,3,17):"holiday_st_patricks",
            date(2027,3,28):"holiday_easter",date(2027,7,4):"holiday_independence",
            date(2027,10,11):"holiday_columbus",date(2027,10,31):"holiday_halloween",
            date(2027,9,12):"holiday_video_games",date(2027,9,8):"holiday_star_trek",
            date(2027,6,20):"holiday_fathers",date(2027,8,13):"holiday_friday_13",
        }
        for day,kind in expected.items():
            self.assertEqual(holiday_on(day)[0],kind,str(day))
        self.assertIsNone(holiday_on(date(2027,4,1)))  # April Fools is NOT a trophy
        self.assertIn("holiday_thanksgiving",ALL_HOLIDAYS)

    def test_star_trek_only_exact_games(self):
        j=sample([("DON","2027-09-08T17:00:00-04:00","50055"),
                  ("SPC","2027-09-08T17:00:00-04:00","50056"),
                  ("VJG","2027-09-08T17:00:00-04:00","50001")])
        _,new=activate(j,blank(),datetime(2027,9,9,tzinfo=timezone.utc),enabled=True)
        self.assertEqual({a["player"] for a in new},{"DON","SPC"})

    def test_olympics_approved_any_game_stack_by_year(self):
        j=sample([("DON","2027-03-25T05:00:00Z","50010"),
                  ("DON","2027-03-26T03:59:59Z","50011"),
                  ("VJG","2027-03-26T04:00:00Z","50012"),
                  ("DON","2028-04-13T17:00:00-04:00","50012"),
                  ("DON","2029-03-29T17:00:00-04:00","50012")])
        # 2028 Holy Thursday is Apr 13; 2029 computed dynamically below.
        _,new=activate(j,blank(),datetime(2030,1,1,tzinfo=timezone.utc),enabled=True)
        olympic=[a for a in new if a["type"].startswith("arcade_olympics")]
        self.assertEqual(len([a for a in olympic if a["type"]=="arcade_olympics_participation"]),3)
        self.assertIn("arcade_olympics_milestone:DON:1",{a["id"] for a in new})
        self.assertIn("arcade_olympics_milestone:DON:3",{a["id"] for a in new})
        self.assertNotIn("arcade_olympics_milestone:DON:5",{a["id"] for a in new})

    def test_holiday_count_once_per_occasion_and_lifetime(self):
        rows=[
            ("DON","2026-12-24T12:00:00-05:00","50010"),
            ("DON","2026-12-25T12:00:00-05:00","50010"),
            ("DON","2026-12-31T12:00:00-05:00","50010"),
            ("DON","2027-01-01T12:00:00-05:00","50010"),
            ("DON","2027-02-14T12:00:00-05:00","50010"),
            ("DON","2027-03-10T12:00:00-05:00","50350"),
            ("DON","2027-03-17T12:00:00-04:00","50010"),
            ("DON","2027-05-04T12:00:00-04:00","50001"),
        ]
        initial=blank()
        updated,new=activate(sample(rows),initial,datetime(2027,6,1,tzinfo=timezone.utc),enabled=True)
        milestones=[a for a in new if a["type"]=="holiday_milestone"]
        self.assertEqual([a["milestone"] for a in milestones],[5])
        self.assertEqual(len([a for a in new if a["type"].startswith("holiday_") and a["type"]!="holiday_milestone"]),2)
        later,repeat=activate(sample(rows),updated,datetime(2027,6,1,tzinfo=timezone.utc),enabled=True)
        self.assertEqual(repeat,[])
        self.assertEqual(later,updated)

    def test_grand_slam_complete_calendar_year_repeatable(self):
        # Complete each of 15 approved holiday types during 2027.
        dates=[
            ("2027-01-01T12:00:00-05:00","50010"),
            ("2027-02-14T12:00:00-05:00","50010"),
            ("2027-03-10T12:00:00-05:00","50350"),
            ("2027-03-17T12:00:00-04:00","50010"),
            ("2027-03-28T12:00:00-04:00","50010"),
            ("2027-05-04T12:00:00-04:00","50001"),
            ("2027-06-20T12:00:00-04:00","50010"),
            ("2027-07-04T12:00:00-04:00","50010"),
            ("2027-08-13T12:00:00-04:00","50010"),
            ("2027-09-08T12:00:00-04:00","50055"),
            ("2027-09-12T12:00:00-04:00","50010"),
            ("2027-10-11T12:00:00-04:00","50010"),
            ("2027-10-31T12:00:00-04:00","50010"),
            ("2027-11-25T12:00:00-05:00","50010"),
            ("2027-12-25T12:00:00-05:00","50010"),
        ]
        j=sample([("DON",dt,gid) for dt,gid in dates])
        _,during=activate(j,blank(),datetime(2027,12,31,21,tzinfo=timezone.utc),enabled=True)
        self.assertFalse(any(a["type"]=="holiday_grand_slam" for a in during))
        next_year,after=activate(j,blank(),datetime(2028,1,2,tzinfo=timezone.utc),enabled=True)
        self.assertIn("holiday_grand_slam:DON:2027",{a["id"] for a in after})
        _,again=activate(j,next_year,datetime(2028,1,2,tzinfo=timezone.utc),enabled=True)
        self.assertEqual(again,[])
        incomplete=sample([("DON",dt,gid) for dt,gid in dates[:-1]])
        _,partial=activate(incomplete,blank(),datetime(2028,1,2,tzinfo=timezone.utc),enabled=True)
        self.assertFalse(any(a["type"]=="holiday_grand_slam" for a in partial))

    def test_future_dates_and_no_april_fools(self):
        j=sample([("DON","2027-04-01T12:00:00-04:00","50010"),
                  ("VJG","2027-10-31T12:00:00-04:00","50010")])
        _,new=activate(j,blank(),datetime(2027,4,2,tzinfo=timezone.utc),enabled=True)
        self.assertEqual(new,[])

    def test_no_backfill_before_activation(self):
        j=sample([("DON","2026-02-14T12:00:00-05:00","50010")])
        _,new=activate(j,blank(),datetime(2027,1,1,tzinfo=timezone.utc),enabled=True)
        self.assertEqual(new,[])

    def test_disabled_by_default(self):
        j=sample([("DON","2027-02-14T12:00:00-05:00","50010")])
        out,new=activate(j,blank(),datetime(2027,3,1,tzinfo=timezone.utc))
        self.assertEqual(out,blank());self.assertEqual(new,[])

if __name__=="__main__":unittest.main()

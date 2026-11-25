#!/usr/bin/env python3
"""Offline launch checks for Christmas, New Year, MAR10, May the Fourth."""
import copy
import unittest
from datetime import datetime, timezone

from seasonal_holiday_awards import activate, MARIO_GAME_IDS, STAR_WARS_GAME_IDS


class SeasonalHolidayTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"schema_version": 1, "awards": [{"id": "holiday_thanksgiving:DON", "type": "holiday_thanksgiving", "player": "DON"}], "verified_plays": [{"event_key": "daily:one"}]}
        self.now = datetime(2027, 5, 6, 12, tzinfo=timezone.utc)

    def journal(self, rows):
        return {"schema_version": 1, "scores": {
            str(sid): {"score_id": str(sid), "name": player, "game": game,
                       "gameName": "Game " + game, "score": 1234, "date": when}
            for sid, (player, game, when) in rows.items()
        }}

    def test_calendar_and_midnight_edges(self):
        j = self.journal({
            1: ("DON", "50010", "2026-12-25T05:00:00Z"),  # 00:00 ET Christmas
            2: ("VJG", "50010", "2026-12-26T04:59:59Z"),  # 23:59:59 ET
            3: ("SPC", "50010", "2026-12-26T05:00:00Z"),  # 00:00 ET Dec 26
            4: ("DAY", "50010", "2027-01-01T05:00:00Z"),  # Jan 1 00:00 ET
            5: ("BGR", "50010", "2027-01-02T04:59:59Z"),  # Jan 1 23:59:59 ET
            6: ("RDG", "50010", "2027-01-02T05:00:00Z"),  # Jan 2
        })
        before = copy.deepcopy(self.ledger)
        updated, new = activate(j, self.ledger, self.now, enabled=True)
        self.assertEqual({(x["player"], x["type"]) for x in new}, {
            ("DON", "holiday_christmas"), ("VJG", "holiday_christmas"),
            ("DAY", "holiday_new_years_day"), ("BGR", "holiday_new_years_day")})
        self.assertEqual(self.ledger, before)
        self.assertEqual(updated["verified_plays"], before["verified_plays"])

    def test_two_day_holiday_windows_and_no_double_trophy(self):
        # First minute of Christmas Eve and last second of Christmas Day count.
        # Same player playing both days earns only the same single lifetime trophy.
        j=self.journal({
            1:("DON","50010","2026-12-24T05:00:00Z"),
            2:("DON","50010","2026-12-25T18:00:00Z"),
            3:("VJG","50010","2026-12-26T04:59:59Z"),
            4:("SPC","50010","2026-12-24T04:59:59Z"), # Dec 23 ET
            5:("DAY","50010","2026-12-31T05:00:00Z"), # Dec 31 00:00 ET
            6:("DAY","50010","2027-01-01T17:00:00Z"),
            7:("BGR","50010","2027-01-02T04:59:59Z"),
            8:("RDG","50010","2027-01-02T05:00:00Z"), # Jan 2 ET
        })
        _,awards=activate(j,self.ledger,self.now,enabled=True)
        self.assertEqual({(a["player"],a["type"]) for a in awards},{
            ("DON","holiday_christmas"),("VJG","holiday_christmas"),
            ("DAY","holiday_new_years_day"),("BGR","holiday_new_years_day")})
        self.assertEqual(len(awards),4)
        self.assertEqual(next(a["date"] for a in awards if a["player"]=="DON"),"2026-12-24")
        self.assertEqual(next(a["date"] for a in awards if a["player"]=="DAY"),"2026-12-31")

    def test_eve_only_as_of_its_date_and_later_approval(self):
        j=self.journal({
            1:("DON","50010","2026-12-24T12:00:00-05:00"),
            2:("VJG","50010","2026-12-31T15:00:00-05:00"),
        })
        _,christmas=activate(j,self.ledger,datetime(2026,12,24,21,0,tzinfo=timezone.utc),enabled=True)
        self.assertEqual([(a["player"],a["type"]) for a in christmas],[("DON","holiday_christmas")])
        _,both=activate(j,self.ledger,datetime(2027,1,3,tzinfo=timezone.utc),enabled=True)
        self.assertEqual({a["player"] for a in both},{"DON","VJG"})

    def test_mario_day_game_whitelist(self):
        self.assertEqual(len(MARIO_GAME_IDS), 8)
        self.assertIn("50032", MARIO_GAME_IDS)  # original Donkey Kong
        self.assertIn("50033", MARIO_GAME_IDS)  # Donkey Kong Jr.
        self.assertNotIn("50034", MARIO_GAME_IDS)  # Donkey Kong 3
        self.assertIn("52039", MARIO_GAME_IDS)  # original Japan variant
        rows = {i + 1: ("DON", gid, "2027-03-10T12:00:00-05:00") for i, gid in enumerate(MARIO_GAME_IDS)}
        rows[20] = ("VJG", "50032", "2027-03-10T12:00:00-05:00")
        rows[21] = ("DAY", "50033", "2027-03-10T12:00:00-05:00")
        rows[22] = ("BGR", "50034", "2027-03-10T12:00:00-05:00")
        rows[23] = ("SPC", "52039", "2027-03-10T12:00:00-05:00")
        rows[24] = ("RDG", "50010", "2027-03-10T12:00:00-05:00")
        _,new = activate(self.journal(rows),self.ledger,self.now,enabled=True)
        self.assertEqual({(x["player"],x["type"]) for x in new},{
            ("DON","holiday_mar10"),("VJG","holiday_mar10"),("DAY","holiday_mar10"),("SPC","holiday_mar10")})

    def test_star_wars_day_game_whitelist(self):
        self.assertEqual(len(STAR_WARS_GAME_IDS), 4)
        rows = {i + 1: ("DON", gid, "2027-05-04T17:00:00-04:00") for i, gid in enumerate(STAR_WARS_GAME_IDS)}
        rows[20] = ("VJG", "50010", "2027-05-04T17:00:00-04:00")
        rows[21] = ("SPC", "50001", "2027-05-05T00:00:00-04:00")
        _,new=activate(self.journal(rows),self.ledger,self.now,enabled=True)
        self.assertEqual([(x["player"],x["type"]) for x in new],[("DON","holiday_may_the_fourth")])

    def test_early_year_excluded(self):
        j=self.journal({1:("DON","50001","2026-05-04T12:00:00-04:00"),
                        2:("VJG","50350","2026-03-10T12:00:00-04:00"),
                        3:("DAY","50010","2026-01-01T12:00:00-05:00")})
        _,new=activate(j,self.ledger,self.now,enabled=True)
        self.assertEqual(new,[])

    def test_iscored_central_time_and_late_approval(self):
        # 23:30 Central 12/25 => 00:30 Eastern 12/26, must not count.
        j=self.journal({1:("DON","50010","2026-12-25 23:30:00"),
                        2:("VJG","50010","2026-12-25 22:30:00")})
        _,new=activate(j,self.ledger,self.now,enabled=True)
        self.assertEqual([a["player"] for a in new],["VJG"])

    def test_one_lifetime_per_holiday(self):
        j=self.journal({1:("DON","50001","2027-05-04T12:00:00-04:00")})
        a,first=activate(j,self.ledger,self.now,enabled=True)
        self.assertEqual(len(first),1)
        b,again=activate(j,a,self.now,enabled=True)
        self.assertEqual(again,[])
        self.assertEqual(b,a)
        future=self.journal({2:("DON","50002","2028-05-04T11:00:00-04:00")})
        _,next_year=activate(future,a,datetime(2028,5,5,tzinfo=timezone.utc),enabled=True)
        self.assertEqual(next_year,[])

    def test_fails_closed(self):
        with self.assertRaises(ValueError):
            activate(self.journal({}),{"schema_version":1,"awards":[]},self.now,enabled=True)
        with self.assertRaises(ValueError):
            activate({"schema_version":1,"scores":{"1":{"score_id":"different"}}},self.ledger,self.now,enabled=True)

    def test_disabled_by_default(self):
        j=self.journal({1:("DON","50001","2027-05-04T12:00:00-04:00")})
        updated, new=activate(j,self.ledger,self.now)
        self.assertEqual(new,[])
        self.assertEqual(updated,self.ledger)


if __name__=="__main__":
    unittest.main()

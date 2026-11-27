#!/usr/bin/env python3
"""Offline date/window checks for holiday push announcements."""
import datetime as dt
from send_holiday_event_push import event_for, easter, nth_weekday
def event(date):return event_for(dt.date.fromisoformat(date))
assert event("2026-11-26")[0]=="thanksgiving"
assert event("2026-11-27") is None
assert event("2026-12-24")[0]=="christmas"
assert event("2026-12-25") is None # Christmas is one announcement for the two-day window
assert event("2026-12-31")[0]=="new_year"
assert event("2027-01-01")[0]=="new_year" # January 1 is the same event, no second push intended
assert event("2027-04-04")[0]=="easter"
assert event("2027-06-20")[0]=="fathers"
assert event("2027-05-04")[0]=="may_fourth"
assert event("2027-09-08")[0]=="star_trek"
assert event("2027-09-12")[0]=="video_games"
assert event("2027-10-11")[0]=="columbus"
assert event("2026-11-13")[0]=="friday_13"
assert event("2026-12-26") is None
print("Holiday event announcement date tests passed")

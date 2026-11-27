#!/usr/bin/env python3
"""Offline calendar regression tests for Holiday Legends push announcements."""
import datetime as dt
from send_holiday_event_push import events_for, easter, nth_weekday

def date(y, m, d):
    return dt.date(y, m, d)

def kinds(day):
    return {event[0] for event in events_for(day)}

def check(day, expected):
    actual = kinds(day)
    assert actual == set(expected), f"{day}: expected {set(expected)!r}, got {actual!r}"

# Independently known Easter dates (not derived from the algorithm under test).
for year, month, day in [
    (2026, 4, 5), (2027, 3, 28), (2028, 4, 16),
    (2029, 4, 1), (2030, 4, 21), (2031, 4, 13),
    (2032, 3, 28),
]:
    assert easter(year) == date(year, month, day), f"Incorrect Easter {year}"

# Build an independent expected event calendar, then check EVERY day of seven
# years. This correctly handles overlaps and non-Friday dates with other holidays.
fixed = {
    (2, 14): "valentines", (3, 10): "mar10",
    (3, 17): "st_patricks", (5, 4): "may_fourth",
    (7, 4): "independence", (9, 8): "star_trek",
    (9, 12): "video_games", (10, 31): "halloween",
    (12, 24): "christmas", (12, 31): "new_year",
}
days_checked = 0
for year in range(2026, 2033):
    expected = {}
    def add(day, kind):
        expected.setdefault(day, set()).add(kind)
    for (month, day), kind in fixed.items():
        add(date(year, month, day), kind)
    add(easter(year), "easter")
    add(nth_weekday(year, 6, 6, 3), "fathers")
    add(nth_weekday(year, 10, 0, 2), "columbus")
    add(nth_weekday(year, 11, 3, 4), "thanksgiving")
    for month in range(1, 13):
        thirteenth = date(year, month, 13)
        if thirteenth.weekday() == 4:
            add(thirteenth, "friday_13")
    day = date(year, 1, 1)
    while day.year == year:
        check(day, expected.get(day, set()))
        days_checked += 1
        day += dt.timedelta(days=1)

# Christmas Eve and New Year's Eve each announce once, not again on the
# second day of the eligibility window.
for year in range(2026, 2033):
    check(date(year, 12, 25), set())
    check(date(year, 1, 1), set())

# Every year has 1-3 Friday the 13ths across the full 400-year Gregorian cycle.
for year in range(2000, 2400):
    fridays = [date(year, month, 13) for month in range(1, 13)
               if date(year, month, 13).weekday() == 4]
    assert 1 <= len(fridays) <= 3, (year, fridays)
    for day in fridays:
        assert "friday_13" in kinds(day)

# Simulate a future overlapping holiday; both must be independently selected.
import send_holiday_event_push as module
original_easter = module.easter
try:
    module.easter = lambda year: date(year, 3, 10)
    check(date(2027, 3, 10), {"mar10", "easter"})
finally:
    module.easter = original_easter

print(f"Holiday calendar tests passed: {days_checked} dates (2026-2032), all 15 events, overlap handling, and 400-year Friday-the-13th guarantee.")

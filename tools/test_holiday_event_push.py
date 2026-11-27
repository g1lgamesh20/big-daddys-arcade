#!/usr/bin/env python3
"""Regression coverage for every Holiday Legends push and moving calendar dates.

This is an offline test. No OneSignal requests are made.
"""
import datetime as dt
from send_holiday_event_push import event_for, events_for, easter, nth_weekday

def check(day, expected):
    actual = event_for(day)
    kind = actual[0] if actual else None
    assert kind == expected, f"{day}: expected {expected!r}, got {kind!r}"

def date(y, m, d):
    return dt.date(y, m, d)

# Independently verified Easter Sundays; catches incorrect algorithm changes.
for year, month, day in [
    (2026, 4, 5), (2027, 3, 28), (2028, 4, 16),
    (2029, 4, 1), (2030, 4, 21),
]:
    assert easter(year) == date(year, month, day), f"Incorrect Easter {year}"

# Check all 15 existing holiday announcement types, every year, plus adjacent
# dates. Christmas and New Year's are single start-of-window announcements.
for year in range(2026, 2033):
    fixed = {
        (2, 14): "valentines",
        (3, 10): "mar10",
        (3, 17): "st_patricks",
        (5, 4): "may_fourth",
        (7, 4): "independence",
        (9, 8): "star_trek",
        (9, 12): "video_games",
        (10, 31): "halloween",
        (12, 24): "christmas",
        (12, 31): "new_year",
    }
    for (month, day), kind in fixed.items():
        check(date(year, month, day), kind)
    check(date(year, 12, 25), None)
    check(date(year, 12, 26), None)
    check(date(year, 1, 1), None)

    moving = [
        (easter(year), "easter"),
        (nth_weekday(year, 6, 6, 3), "fathers"),
        (nth_weekday(year, 10, 0, 2), "columbus"),
        (nth_weekday(year, 11, 3, 4), "thanksgiving"),
    ]
    for day, kind in moving:
        check(day, kind)
        for neighbor in [day - dt.timedelta(days=1), day + dt.timedelta(days=1)]:
            # An adjacent day can legitimately be another holiday.
            if neighbor.month == 3 and neighbor.day == 10:
                continue
            if neighbor.day == 13 and neighbor.weekday() == 4:
                continue
            check(neighbor, None)

    # Every Friday the 13th in the year, not just one sample.
    for month in range(1, 13):
        thirteenth = date(year, month, 13)
        if thirteenth.weekday() == 4:
            check(thirteenth, "friday_13")
        else:
            check(thirteenth, None)

# Targeted regressions for previously failed preview and date windows.
check(date(2027, 3, 10), "mar10")
check(date(2027, 3, 28), "easter")
check(date(2027, 4, 4), None)
check(date(2026, 11, 26), "thanksgiving")
check(date(2026, 11, 27), None)
check(date(2026, 12, 24), "christmas")
check(date(2026, 12, 31), "new_year")
check(date(2027, 1, 1), None)

print("All Holiday Legends event dates and announcement windows passed (2026–2032).")

# Every Gregorian calendar year has at least one Friday the 13th.
for year in range(2000, 2400):
    fridays = [date(year, month, 13) for month in range(1, 13)
               if date(year, month, 13).weekday() == 4]
    assert 1 <= len(fridays) <= 3, (year, fridays)
    for day in fridays:
        assert "friday_13" in [item[0] for item in events_for(day)]

# Collision example: September 13, 2030 is Friday the 13th, and 2030-09-13
# may be checked alongside its neighboring Video Games Day announcement.
# Test an actual overlap: May 13, 2028 is Friday the 13th only.
# More generally, a future event added to an existing date must not replace it.
import send_holiday_event_push as module
original_easter = module.easter
try:
    module.easter = lambda year: date(year, 3, 10)
    assert [item[0] for item in events_for(date(2027, 3, 10))] == ["mar10", "easter"]
finally:
    module.easter = original_easter
print("Overlap and Friday-the-13th guarantee checks passed.")

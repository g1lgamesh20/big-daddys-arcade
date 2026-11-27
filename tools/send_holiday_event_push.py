#!/usr/bin/env python3
"""Holiday Legends event-start OneSignal pushes. Does not issue achievements."""
import argparse
import datetime as dt
import json
import os
import sys
import uuid
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
APP_ID = "6aca5b1a-5845-489a-a739-4d979d7f7cb4"
ARCADE_URL = "https://g1lgamesh20.github.io/big-daddys-arcade/"

def nth_weekday(year, month, weekday, nth):
    first = dt.date(year, month, 1)
    return first + dt.timedelta(days=(weekday - first.weekday()) % 7 + 7 * (nth - 1))

def easter(year):
    a=year%19; b=year//100; c=year%100; d=b//4; e=b%4
    f=(b+8)//25; g=(b-f+1)//3
    h=(19*a+b-d-g+15)%30; i=c//4; k=c%4
    l=(32+2*e+2*i-h-k)%7; m=(a+11*h+22*l)//451
    month=(h+l-7*m+114)//31
    day=(h+l-7*m+114)%31+1
    return dt.date(year,month,day)

def events_for(day):
    y,m,d=day.year,day.month,day.day
    events={
      (2,14):("valentines","💘 HAPPY VALENTINE'S DAY!","Love at first byte! Play today for a shot at LOVE AT FIRST BYTE."),
      (3,10):("mar10","🍄 HAPPY MAR10 DAY!","It's-a me, high score! Play an eligible Mario game today to chase MAR10 DAY HERO."),
      (3,17):("st_patricks","☘️ HAPPY ST. PATRICK'S DAY!","Feeling lucky? Chase LUCK OF THE ARCADE with a score today!"),
      (5,4):("may_fourth","🌌 MAY THE FOURTH BE WITH YOU!","Use the score, Luke! Play an eligible Star Wars arcade game today for the holiday achievement."),
      (7,4):("independence","🇺🇸 HAPPY FOURTH OF JULY!","Let freedom ring and high scores soar! Play today for RED, WHITE & HIGH SCORE!"),
      (9,8):("star_trek","🖖 HAPPY STAR TREK DAY!","Live long and high score! Play an eligible Star Trek game today for the holiday achievement."),
      (9,12):("video_games","🕹️ HAPPY VIDEO GAMES DAY!","You were born to game! Submit a score today for BORN TO GAME!"),
      (10,31):("halloween","🎃 HAPPY HALLOWEEN!","No tricks, just high scores! Play today to haunt the leaderboard and chase MONSTER MASHER."),
      (12,24):("christmas","🎄 MERRY CHRISTMAS!","Santa checks his list; we check the leaderboards! Play Dec 24–25 to chase SANTA'S HIGH SCORE HELPER."),
      (12,31):("new_year","🎆 HAPPY NEW YEAR'S EVE!","New year, new high scores, same old rivalries! Play Dec 31–Jan 1 to chase NEW YEAR, NEW HIGH SCORE!"),
    }
    matches = []
    if (m,d) in events: matches.append(events[m,d])
    if day==easter(y): matches.append(("easter","🐰 HAPPY EASTER!","Hop to the leaderboard! Play today for the EGG-STRA LIFE! achievement."))
    if day==nth_weekday(y,6,6,3): matches.append(("fathers","👨 HAPPY FATHER'S DAY!","Dad's got game! Put up a score today and chase DAD'S GOT GAME!"))
    if day==nth_weekday(y,10,0,2): matches.append(("columbus","🧭 HAPPY COLUMBUS DAY!","Explore a new high score today and chase THE HIGH SCORE EXPLORER!"))
    if day==nth_weekday(y,11,3,4): matches.append(("thanksgiving","🦃 HAPPY THANKSGIVING!","Stuff your face, then stuff the leaderboard! Play today for TURKEY DAY GAMER."))
    if d==13 and day.weekday()==4: matches.append(("friday_13","😱 WATCH OUT! IT'S FRIDAY THE 13TH!","Unlucky for some, legendary for you! Play today for UNLUCKY FOR SOME!"))
    return matches

def event_for(day):
    """Backward-compatible first event for existing callers."""
    matches = events_for(day)
    return matches[0] if matches else None

def run():
    parser=argparse.ArgumentParser()
    parser.add_argument("--date",help="Eastern YYYY-MM-DD for dry-run preview")
    parser.add_argument("--send",action="store_true",help="Send real push (workflow only)")
    args=parser.parse_args()
    now=dt.datetime.now(EASTERN)
    day=dt.date.fromisoformat(args.date) if args.date else now.date()
    if args.date and args.send: raise ValueError("Date overrides are preview-only")
    if args.send and now.hour!=9:
        print("Outside 9 AM Eastern announcement hour; skipping.")
        return
    events=events_for(day)
    if not events:
        print("No Holiday Legends announcement on",day)
        return
    key=os.environ.get("ONESIGNAL_REST_API_KEY","").strip() if args.send else ""
    if args.send and not key: raise ValueError("Missing ONESIGNAL_REST_API_KEY")
    for kind,title,body in events:
        print(json.dumps({"date":day.isoformat(),"event":kind,"title":title,"message":body,"send":args.send},ensure_ascii=False))
        if not args.send: continue
        # Stable per-event/date idempotency: overlapping events remain independent.
        idem=str(uuid.uuid5(uuid.NAMESPACE_URL,"big-daddys-arcade:holiday-push:"+day.isoformat()+":"+kind))
        payload={"app_id":APP_ID,"included_segments":["All"],"headings":{"en":title},
                 "contents":{"en":body},"url":ARCADE_URL,"idempotency_key":idem,
                 "data":{"kind":"holiday_announcement","holiday":kind,"date":day.isoformat()}}
        req=Request("https://api.onesignal.com/notifications",
                    data=json.dumps(payload).encode(),
                    headers={"Authorization":"Key "+key,"Content-Type":"application/json","Accept":"application/json"},
                    method="POST")
        try:
            with urlopen(req,timeout=30) as response:
                result=json.load(response)
            if not result.get("id"): raise RuntimeError("OneSignal did not confirm notification ID")
            print("OneSignal accepted holiday push:",result["id"])
        except HTTPError as exc: raise RuntimeError("OneSignal HTTP "+str(exc.code)) from None
        except URLError as exc: raise RuntimeError("OneSignal connection failed") from exc

if __name__=="__main__":
    try:run()
    except (ValueError,RuntimeError) as exc:
        print("Holiday push failed:",exc,file=sys.stderr)
        sys.exit(1)

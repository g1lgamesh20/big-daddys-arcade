#!/usr/bin/env python3
"""Holiday Legends Wave 2, cumulative occasions and Holy Thursday Arcade Olympics.

Only immutable, approved iScored original-submission evidence (post-fix).
Individual holiday trophies are lifetime; participation records are counted once
per holiday occasion per player and can earn cumulative milestones. No push.
April Fools is deliberately absent from all award rules.
"""
import copy
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from iscored_timestamp import parse_iscored_time
from seasonal_holiday_awards import HOLIDAYS as ORIGINAL_HOLIDAYS, active_on

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "secret-score-evidence.json"
LEDGER = ROOT / "verified-challenge-awards.json"
EASTERN = ZoneInfo("America/New_York")
PLAYER = re.compile(r"^[A-Z0-9 ]{1,3}$")
STAR_TREK_IDS = frozenset(("50055", "50056"))
WAVE_START = date(2027, 1, 1)
MILESTONES = ((5,"THE HOLIDAY REGULAR"),(10,"HOLIDAY WARRIOR"),(25,"HOLIDAY HERO"),
              (50,"HOLIDAY SUPERSTAR"),(100,"THE HOLIDAY IMMORTAL"))
OLYMPIC_MILESTONES = ((1,"ARCADE OLYMPIAN"),(3,"OLYMPIC VETERAN"),
                      (5,"OLYMPIC LEGEND"),(10,"OLYMPIC IMMORTAL"))
WAVE_HOLIDAYS = {
    "holiday_valentines":("LOVE AT FIRST BYTE",None),
    "holiday_st_patricks":("LUCK OF THE ARCADE",None),
    "holiday_easter":("EGG-STRA LIFE!",None),
    "holiday_independence":("RED, WHITE & HIGH SCORE!",None),
    "holiday_columbus":("THE HIGH SCORE EXPLORER",None),
    "holiday_halloween":("MONSTER MASHER",None),
    "holiday_video_games":("BORN TO GAME!",None),
    "holiday_star_trek":("LIVE LONG AND HIGH SCORE!",STAR_TREK_IDS),
    "holiday_fathers":("DAD'S GOT GAME!",None),
    "holiday_friday_13":("UNLUCKY FOR SOME!",None),
}
# Existing first-generation holidays also count toward occasion totals.
EXISTING_HOLIDAYS = frozenset(("holiday_thanksgiving",)+tuple({r[0] for r in ORIGINAL_HOLIDAYS.values()}))
ALL_HOLIDAYS = frozenset(WAVE_HOLIDAYS) | EXISTING_HOLIDAYS

def easter(year):
    """Gregorian computus: Easter Sunday."""
    a=year%19;b=year//100;c=year%100;d=b//4;e=b%4
    f=(b+8)//25;g=(b-f+1)//3
    h=(19*a+b-d-g+15)%30;i=c//4;k=c%4
    ell=(32+2*e+2*i-h-k)%7
    m=(a+11*h+22*ell)//451
    month=(h+ell-7*m+114)//31
    day=(h+ell-7*m+114)%31+1
    return date(year,month,day)

def nth_weekday(year,month,weekday,n):
    first=date(year,month,1)
    return date(year,month,1+(weekday-first.weekday())%7+7*(n-1))

def thanksgiving(year):
    return nth_weekday(year,11,3,4)

def holy_thursday(year):
    return easter(year)-timedelta(days=3)

def holiday_on(day):
    """Return (kind, game IDs or None, year-of-occasion) or None."""
    y,m,d=day.year,day.month,day.day
    wave={
        (2,14):"holiday_valentines",
        (3,17):"holiday_st_patricks",
        (7,4):"holiday_independence",
        (10,31):"holiday_halloween",
        (9,12):"holiday_video_games",
        (9,8):"holiday_star_trek",
    }
    kind=wave.get((m,d))
    if day==easter(y):kind="holiday_easter"
    if day==nth_weekday(y,10,0,2):kind="holiday_columbus"
    if day==nth_weekday(y,6,6,3):kind="holiday_fathers"
    if d==13 and day.weekday()==4:kind="holiday_friday_13"
    if kind and day>=WAVE_START:
        return kind,WAVE_HOLIDAYS[kind][1],y
    if day==thanksgiving(y) and day>=date(2026,11,26):
        return "holiday_thanksgiving",None,y
    original=ORIGINAL_HOLIDAYS.get((m,d))
    if original and active_on(day,original[0]):
        # Dec 31 belongs to the following New Year's holiday year.
        occasion_year=y+1 if original[0]=="holiday_new_years_day" and m==12 else y
        return original[0],original[2],occasion_year
    return None

def occasion_key(day,kind,year):
    # A holiday has one annual occurrence, except each Friday 13 is distinct.
    return f"{kind}:{day.isoformat() if kind=='holiday_friday_13' else year}"

def eligible_scores(journal,now):
    if journal.get("schema_version")!=1 or not isinstance(journal.get("scores"),dict):
        raise ValueError("Malformed approved-score evidence journal")
    now_et=now.astimezone(EASTERN)
    for sid,row in journal["scores"].items():
        if not isinstance(row,dict) or str(row.get("score_id"))!=str(sid):
            raise ValueError("Conflicting approved-score journal ID")
        player=row.get("name")
        if not isinstance(player,str) or not PLAYER.fullmatch(player) or not player.strip():
            continue
        when=parse_iscored_time(row.get("date"))
        if when is None or when>now_et:continue
        day=when.date()
        event=holiday_on(day)
        olympics=day>=WAVE_START and day==holy_thursday(day.year)
        if not event and not olympics:continue
        gid=str(row.get("game") or "").strip()
        if not gid or isinstance(row.get("score"),bool):continue
        try:points=int(row.get("score"))
        except (ValueError,TypeError):continue
        if points<0:continue
        if event and event[1] is not None and gid not in event[1]:event=None
        if event or olympics:
            yield player,when,str(sid),row,points,event,olympics

def activate(journal,ledger,now,*,enabled=False):
    if not enabled:return copy.deepcopy(ledger),[]
    if now.tzinfo is None or now.utcoffset() is None:raise ValueError("Timezone-aware now required")
    if ledger.get("schema_version")!=1 or not isinstance(ledger.get("awards"),list) or not isinstance(ledger.get("verified_plays"),list):
        raise ValueError("Malformed permanent award ledger")
    out=copy.deepcopy(ledger);ids=set()
    for award in out["awards"]:
        if not isinstance(award,dict) or not isinstance(award.get("id"),str) or not award["id"] or award["id"] in ids:
            raise ValueError("Duplicate or invalid existing award")
        ids.add(award["id"])
    # Earliest approved score for each holiday occasion and each annual Olympics.
    occasions={};olympics={}
    for player,when,sid,row,points,event,is_olympics in eligible_scores(journal,now):
        payload=(when,sid,row,points)
        if event:
            kind,_,year=event
            key=(player,occasion_key(when.date(),kind,year),kind,year)
            if key not in occasions or payload[:2]<occasions[key][:2]:
                occasions[key]=payload
        if is_olympics:
            key=(player,when.year)
            if key not in olympics or payload[:2]<olympics[key][:2]:
                olympics[key]=payload
    added=[]
    def issue(kind,name,player,when,sid,row,points,award_id,**metadata):
        if award_id in ids:return
        award={"id":award_id,"type":kind,"name":name,"player":player,
            "date":when.date().isoformat(),"game":str(row.get("gameName") or "")[:100],
            "game_id":str(row["game"]),"score":points,"score_id":sid,
            "original_submitted_at_et":when.isoformat(),
            "verified_at":now.astimezone(timezone.utc).isoformat(),
            "verification_method":"approved_iscored_original_submission_timestamp",
            **metadata}
        out["awards"].append(award);added.append(award);ids.add(award_id)
    grouped=defaultdict(list)
    for (player,key,kind,year),payload in occasions.items():
        grouped[player].append((payload[0],key,kind,year,payload))
        if kind in WAVE_HOLIDAYS:
            issue(kind,WAVE_HOLIDAYS[kind][0],player,*payload,kind+":"+player,occasion_key=key)
    for player,events in grouped.items():
        events.sort(key=lambda x:(x[0],x[1]))
        for threshold,name in MILESTONES:
            if len(events)<threshold:continue
            when,key,kind,year,payload=events[threshold-1]
            issue("holiday_milestone",name,player,*payload,
                  f"holiday_milestone:{player}:{threshold}",milestone=threshold,occasion_key=key)
        # Full year requires all designated holiday TYPES (not repeated Friday 13s),
        # and is only issued when that Eastern calendar year has ended.
        years=defaultdict(set);first_by_year={}
        for when,key,kind,year,payload in events:
            years[year].add(kind)
            first_by_year[(year,kind)]=(when,payload)
        required=ALL_HOLIDAYS
        for year,kinds in years.items():
            if year < 2027 or not required.issubset(kinds):continue
            if now.astimezone(EASTERN).date()<=date(year,12,31):continue
            when,payload=sorted((v for (y,k),v in first_by_year.items() if y==year),key=lambda x:x[0])[-1]
            issue("holiday_grand_slam","HOLIDAY GRAND SLAM!",player,*payload,
                  f"holiday_grand_slam:{player}:{year}",event_year=year)
    olympic_by_player=defaultdict(list)
    for (player,year),payload in olympics.items():
        olympic_by_player[player].append((year,payload))
    for player,events in olympic_by_player.items():
        events.sort()
        for year,payload in events:
            issue("arcade_olympics_participation","ARCADE OLYMPIAN",player,*payload,
                  f"arcade_olympics_participation:{player}:{year}",event_year=year)
        for threshold,name in OLYMPIC_MILESTONES:
            if len(events)<threshold:continue
            year,payload=events[threshold-1]
            issue("arcade_olympics_milestone",name,player,*payload,
                  f"arcade_olympics_milestone:{player}:{threshold}",milestone=threshold,event_year=year)
    out["awards"].sort(key=lambda a:(str(a.get("date","")),str(a.get("id",""))))
    return out,added

def main():
    if os.environ.get("HOLIDAY_WAVE2_AWARDS_ENABLED")!="1":
        print("Wave 2 holiday awards disabled");return
    journal=json.loads(JOURNAL.read_text(encoding="utf-8"))
    ledger=json.loads(LEDGER.read_text(encoding="utf-8"))
    updated,added=activate(journal,ledger,datetime.now(timezone.utc),enabled=True)
    if added:
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=LEDGER.parent,
             prefix=".holiday-wave2-",suffix=".json",delete=False) as t:
            json.dump(updated,t,indent=2,ensure_ascii=False);t.write("\n");p=Path(t.name)
        p.replace(LEDGER)
    print("Wave 2 holiday / Olympics awards:",len(added),"no notifications")

if __name__=="__main__":main()

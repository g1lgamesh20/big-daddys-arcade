#!/usr/bin/env python3
"""Mirror server-evaluated social trophies into the permanent GitHub ledger.

Prospective events only; no push notifications. Self-entered initials are not
authenticated player identity. Fail closed if the Supabase endpoint is unavailable.
"""
import json
import tempfile
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/"verified-challenge-awards.json"
ENDPOINT="https://jrqzwlowxofnyqpmjgkg.supabase.co/functions/v1/arcade-social-awards"
NAMES={
  "trash_talk":["Trash Talk Rookie","Trash Talk Regular","Trash Talk Veteran","Trash Talk Legend","Master of Banter","Arcade Mouthpiece"],
  "give_props":["Props Giver","Hi 5!","Good Sport","Hype Squad","Community Champion","Props Legend"]
}
THRESHOLDS=(1,5,10,25,50,100)

def validate_award(a):
    if not isinstance(a,dict): raise ValueError("Invalid social trophy row")
    player=a.get("player")
    if not isinstance(player,str) or not 1<=len(player)<=3 or not player.strip() or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 " for c in player):
        raise ValueError("Invalid player")
    kind=a.get("type")
    if kind=="secret_props_machine":
        expected_id="secret_props_machine:"+player
        expected_name="PROPS MACHINE!"
    elif kind in ("social_trash_talk","social_give_props"):
        threshold=a.get("milestone")
        if threshold not in THRESHOLDS or type(threshold) is not int: raise ValueError("Invalid milestone")
        expected_id=kind+":"+player+":"+str(threshold)
        expected_name=NAMES[kind.removeprefix("social_")][THRESHOLDS.index(threshold)]
    else: raise ValueError("Unexpected trophy type")
    if a.get("id")!=expected_id or a.get("name")!=expected_name: raise ValueError("Inconsistent trophy")
    day=a.get("date")
    if not isinstance(day,str) or date.fromisoformat(day).isoformat()!=day: raise ValueError("Invalid day")
    return {"id":expected_id,"type":kind,"name":expected_name,"player":player,
            "date":day,"verification_method":"prospective_server_recorded_social_event_self_entered_initials",
            **({"milestone":a["milestone"]} if kind!="secret_props_machine" else {})}

def merge(ledger,payload):
    if ledger.get("schema_version")!=1 or not isinstance(ledger.get("awards"),list):
        raise ValueError("Invalid ledger")
    if payload.get("schema_version")!=1 or payload.get("prospective_only") is not True or not isinstance(payload.get("awards"),list):
        raise ValueError("Invalid social award feed")
    result=json.loads(json.dumps(ledger))
    seen={a.get("id") for a in result["awards"] if isinstance(a,dict)}
    new=[]
    for row in payload["awards"]:
        award=validate_award(row)
        if award["id"] in seen: continue
        seen.add(award["id"])
        result["awards"].append(award)
        new.append(award)
    return result,new

def main():
    with urlopen(Request(ENDPOINT,headers={"Accept":"application/json","User-Agent":"BigDaddysArcadeSocialTrophies/1.0"}),timeout=20) as response:
        if response.status!=200: raise RuntimeError("Social trophy evaluator unavailable")
        payload=json.load(response)
    existing=json.loads(LEDGER.read_text(encoding="utf-8"))
    updated,new=merge(existing,payload)
    if new:
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=LEDGER.parent,
             prefix=".social-trophies-",suffix=".json",delete=False) as tmp:
            json.dump(updated,tmp,indent=2,ensure_ascii=False)
            tmp.write("\n")
            temp=Path(tmp.name)
        temp.replace(LEDGER)
    print("Prospective social trophies:",len(new),"new permanent awards (NO notifications)")

if __name__=="__main__": main()

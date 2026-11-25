#!/usr/bin/env python3
"""April Fools Arcade News prank, scheduled at 9 AM America/New_York.

No award is minted. Only an Arcade News bulletin and OneSignal notification.
Two deterministic yearly events, the tease Apr 1 and reveal Apr 2.
OneSignal idempotency keys are stable per event for retry safety.
"""
import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "arcade-news.json"
STATE = ROOT / "april-fools-notification-state.json"
NY = ZoneInfo("America/New_York")
APP_ID = "6aca5b1a-5845-489a-a739-4d979d7f7cb4"
JOKE = "APRIL FOOLS! You didn't really think we were giving out a trophy THAT easily, did you?"
EVENTS = {
    1: ("🏆 THE ULTIMATE ARCADE LEGEND!",
        "A mysterious, limited-time achievement has appeared! Play today to unlock the most prestigious trophy in arcade history!"),
    2: ("🤡 APRIL FOOLS!",
        JOKE),
}

def event_at(now):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("A timezone-aware clock is required")
    local=now.astimezone(NY)
    if local.month!=4 or local.day not in EVENTS or local.hour<9:
        return None
    key=f"april-fools:{local.year}:{local.day:02d}"
    return key,EVENTS[local.day][0],EVENTS[local.day][1]

def load_state():
    if not STATE.exists():return {"schema_version":1,"sent":[]}
    value=json.loads(STATE.read_text(encoding="utf-8"))
    if value.get("schema_version")!=1 or not isinstance(value.get("sent"),list):
        raise ValueError("Malformed April Fools push state")
    return value

def publish(now):
    event=event_at(now)
    if event is None:return False
    key,title,message=event
    data=json.loads(NEWS.read_text(encoding="utf-8"))
    items=data.get("bulletins")
    if not isinstance(items,list):raise ValueError("Malformed Arcade News bulletin archive")
    if any(item.get("id")==key for item in items if isinstance(item,dict)):
        return False
    items.insert(0,{"id":key,"title":title,"message":message,
                     "created_at":now.astimezone(timezone.utc).isoformat()})
    NEWS.write_text(json.dumps({"bulletins":items[:100]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return True

def payload(key,title,message):
    return {
        "app_id":APP_ID,"included_segments":["All"],
        "headings":{"en":title},"contents":{"en":message},
        "url":"https://g1lgamesh20.github.io/big-daddys-arcade/#arcade-news",
        "data":{"kind":"arcade_news","bulletin_id":key},
        "idempotency_key":str(uuid.uuid5(uuid.NAMESPACE_URL,"big-daddys-arcade/"+key)),
    }

def send(now,opener=urlopen,key=None):
    event=event_at(now)
    if event is None:return False
    event_key,title,message=event
    state=load_state()
    if event_key in state["sent"]:return False
    # Never push a phantom bulletin if the archive is not already committed.
    published=json.loads(NEWS.read_text(encoding="utf-8"))
    if not any(x.get("id")==event_key for x in published.get("bulletins",[]) if isinstance(x,dict)):
        raise RuntimeError("Arcade News bulletin not archived before push")
    auth=key if key is not None else os.getenv("ONESIGNAL_REST_API_KEY","")
    if not auth:raise RuntimeError("Missing OneSignal REST API key")
    request=Request("https://api.onesignal.com/notifications",
       data=json.dumps(payload(event_key,title,message)).encode("utf-8"),
       headers={"Authorization":"Key "+auth,"Content-Type":"application/json","Accept":"application/json"},
       method="POST")
    with opener(request,timeout=30) as response:
        answer=json.load(response)
    if not answer.get("id"):raise RuntimeError("OneSignal did not accept announcement")
    state["sent"].append(event_key)
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return True

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["publish","send"])
    args=parser.parse_args()
    now=datetime.now(timezone.utc)
    done=publish(now) if args.action=="publish" else send(now)
    print("April Fools",args.action,"changed=",done, "event=",event_at(now))

if __name__=="__main__":main()

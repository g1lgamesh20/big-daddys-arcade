#!/usr/bin/env python3
"""Read-only exact score lookup for iScored's public API; no source data altered."""
import json
from urllib.request import Request, urlopen

URL="https://www.iScored.info/api/G1LGAMESH/getAllScores"
TARGET_PLAYER="DAY"
TARGET_SCORE=10602900

def main():
    req=Request(URL,headers={"Accept":"application/json","User-Agent":"BigDaddysArcadeReadOnlyApprovalCheck/1.0"})
    with urlopen(req,timeout=40) as response:
        raw=json.load(response)
    rows=raw.get("scores") if isinstance(raw,dict) else None
    if not isinstance(rows,list):
        raise ValueError("Public iScored API missing scores array")
    print("Public API returned",len(rows),"score entries")
    exact=[]
    ghost=[]
    for row in rows:
        if not isinstance(row,dict):continue
        player=str(row.get("name") or "").strip().upper()
        game=str(row.get("gameName") or "").strip()
        try:score=int(row.get("score"))
        except (ValueError,TypeError):continue
        if "ghostbusters" in game.casefold():
            ghost.append({"game":game,"game_id":str(row.get("game")),
                          "player":player,"score":score,
                          "submission_date_raw":str(row.get("date") or ""),
                          "score_id":str(row.get("id") or "")})
        if player==TARGET_PLAYER and score==TARGET_SCORE:
            exact.append({"game":game,"game_id":str(row.get("game")),
                          "player":player,"score":score,
                          "submission_date_raw":str(row.get("date") or ""),
                          "score_id":str(row.get("id") or "")})
    print("EXACT DAY 10,602,900 MATCHES:",json.dumps(exact,ensure_ascii=False))
    if not exact:
        print("No exact match in current public API snapshot. This does NOT prove the score was unapproved.")
    print("GHOSTBUSTERS PUBLIC ENTRIES:",json.dumps(ghost,ensure_ascii=False))
    print("READ-ONLY CHECK COMPLETE. No data, trophy, approval, or push modified.")

if __name__=="__main__":main()

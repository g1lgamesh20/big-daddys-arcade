#!/usr/bin/env python3
"""Build sanitized public scoreboard from read-only iScored API.
No emails, internal IDs, or raw API payload are written to GitHub Pages.
PAPA calculation is an approximation pending verification of iScored tie/rank rules.
"""
import json
import hashlib
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen

URL = os.environ.get('ISCORED_READ_URL', 'https://www.iScored.info/api/G1LGAMESH/getAllScores')
OUTPUT = Path(__file__).resolve().parents[1] / 'legends.json'
STATE = OUTPUT.with_name('medal-state.json')
FEED = OUTPUT.with_name('medals.json')
RECORDS = OUTPUT.with_name('arcade-records.json')
DAILY = OUTPUT.with_name('daily-champion.json')

def papa_points(rank):
    if rank == 1: return 100
    if rank == 2: return 90
    return max(0, 88 - rank)  # 3rd=85, 4th=84, ..., 88th=0

def build(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('scores'), list):
        raise ValueError('Unexpected iScored response: missing scores array')
    by_game = {}
    valid = []
    for row in raw['scores']:
        if not isinstance(row, dict): continue
        player = str(row.get('name') or '').strip().upper()[:48]
        game = str(row.get('gameName') or '').strip()[:100]
        game_id = row.get('game')
        score = row.get('score')
        date = str(row.get('date') or '')
        if not player or not game or game_id is None or isinstance(score, bool): continue
        try: score = int(score)
        except (ValueError, TypeError): continue
        if score < 0: continue
        record = {'player':player, 'game':game, 'game_id':str(game_id), 'score':score, 'date':date, 'score_id':str(row.get('id') or '')}
        valid.append(record)
        key = (str(game_id), player)
        if key not in by_game or score > by_game[key]['score']:
            by_game[key] = record
    games = {}
    for row in by_game.values(): games.setdefault(row['game_id'], []).append(row)
    champions = []
    per_player = {}
    for group in games.values():
        # Competition ranking: ties share rank; next rank skips positions.
        group.sort(key=lambda x:(-x['score'],x['player']))
        last_score = None
        rank = 0
        for i, row in enumerate(group):
            if row['score'] != last_score: rank = i+1
            last_score = row['score']
            per_player.setdefault(row['player'], []).append(papa_points(rank))
            if rank == 1: champions.append({**row, 'rank':1})
    # Current medal positions across all games (not lifetime medal alerts).
    podium_counts = {player: {'gold': 0, 'silver': 0, 'bronze': 0} for player in per_player}
    for group in games.values():
        group.sort(key=lambda x: (-x['score'], x['player']))
        prior_score = None
        rank = 0
        for i, row in enumerate(group):
            if row['score'] != prior_score:
                rank = i + 1
            prior_score = row['score']
            if rank in (1, 2, 3):
                podium_counts[row['player']][('gold', 'silver', 'bronze')[rank - 1]] += 1
    standings = [{'player':player,'points':sum(sorted(points,reverse=True)[:1000]),
                  'games':len(points), **podium_counts[player]}
                 for player,points in per_player.items()]
    standings.sort(key=lambda x:(-x['points'],-x['games'],x['player']))
    recent = sorted(valid,key=lambda x:x['date'],reverse=True)[:12]
    champions.sort(key=lambda x:(x['game'].casefold(),x['player']))
    return {'updated_at':datetime.now(timezone.utc).isoformat(),
            'source':'iScored public read API',
            'scoring_note':'PAPA-style estimate: top 1000 games per player; one best score per player per game; competition ties. iScored may handle ties differently.',
            'standings':standings,
            'champions':champions,
            'entries': [{'kind':'champion',**row} for row in champions[:120]] + [{'kind':'recent',**row} for row in recent],
            'total_games':len(games),'total_players':len(per_player)}


def update_daily_champion(champions, updated_at):
    """Persist daily game IDs; preselect tomorrow so midnight ET needs no Action run."""
    today = datetime.now(ZoneInfo('America/New_York')).date()
    existing = {}
    if DAILY.exists():
        try:
            old = json.loads(DAILY.read_text(encoding='utf-8'))
            existing = {item['date']:item for item in old.get('days', [])
                        if isinstance(item, dict) and isinstance(item.get('date'), str)
                        and isinstance(item.get('game_id'), str)}
        except (ValueError, OSError, TypeError):
            existing = {}
    # One entry per game ID, not per tied first-place player.
    eligible = {str(row['game_id']):row['game'] for row in champions
                if str(row.get('game', '')).strip().casefold() != 'test game'}
    if not eligible:
        return
    days = []
    previous = existing.get((today-timedelta(days=1)).isoformat())
    if previous and previous['game_id'] in eligible:
        days.append(previous)
    for offset in (0, 1):
        date = (today+timedelta(days=offset)).isoformat()
        prior = existing.get(date)
        avoid = days[-1]['game_id'] if days else None
        if prior and prior['game_id'] in eligible and (prior['game_id'] != avoid or len(eligible) == 1):
            # Preserve valid announced selections, but repair removed games and repeats.
            chosen = {**prior, 'game':eligible[prior['game_id']]}
        else:
            choices = sorted(k for k in eligible if k != avoid)
            if not choices:  # Only one game available; repeating is unavoidable.
                choices = sorted(eligible)
            # Stable selection, independent of score order or runtime hash seeds.
            digest = hashlib.sha256(('BigDaddysArcade:'+date).encode()).digest()
            game_id = choices[int.from_bytes(digest[:8], 'big') % len(choices)]
            chosen = {'date':date, 'game_id':game_id, 'game':eligible[game_id]}
        days.append(chosen)
    DAILY.write_text(json.dumps({'updated_at':updated_at, 'timezone':'America/New_York',
                                 'days':days},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    req = Request(URL,headers={'User-Agent':'BigDaddysArcadeLegends/1.7','Accept':'application/json'})
    with urlopen(req,timeout=25) as response:
        if response.status != 200: raise RuntimeError('iScored returned HTTP '+str(response.status))
        raw = json.load(response)
    result = build(raw)
    if not result['entries']: raise RuntimeError('No valid scores; preserving previous scoreboard')
    # Rank each player's single best score per game, not all their submissions.
    # Bootstrap without notifications; only newly observed score IDs can alert.
    groups = {}
    for row in raw['scores']:
        if not isinstance(row, dict): continue
        name = str(row.get('name') or '').strip().upper()[:48]
        game = str(row.get('gameName') or '').strip()[:100]
        game_id = row.get('game')
        sid = row.get('id')
        try: score = int(row.get('score'))
        except (TypeError, ValueError): continue
        if not name or not game or game_id is None or sid is None or score < 0: continue
        key = (str(game_id), name)
        candidate = {'id':str(sid),'player':name,'game':game,'game_id':str(game_id),'score':score,'date':str(row.get('date') or '')}
        if key not in groups or score > groups[key]['score'] or (score == groups[key]['score'] and candidate['date'] > groups[key]['date']):
            groups[key] = candidate
    per_game = {}
    for entry in groups.values(): per_game.setdefault(entry['game_id'], []).append(entry)
    podium = []
    for entries in per_game.values():
        entries.sort(key=lambda x:(-x['score'], x['player']))
        prev = None
        rank = 0
        for i, entry in enumerate(entries):
            if entry['score'] != prev: rank = i+1
            prev = entry['score']
            if rank <= 3: podium.append({**entry,'rank':rank,'medal':('gold','silver','bronze')[rank-1]})
    all_ids = {str(row.get('id')) for row in raw['scores'] if isinstance(row,dict) and row.get('id') is not None}
    if STATE.exists():
        state = json.loads(STATE.read_text(encoding='utf-8'))
        known = set(str(x) for x in state.get('known_ids',[]))
        prior = json.loads(FEED.read_text(encoding='utf-8')) if FEED.exists() else {'alerts':[]}
        alerts = [entry for entry in podium if entry['id'] not in known]
        alerts.sort(key=lambda x:(x['date'],x['id']),reverse=True)
        # Retain past alerts; do not re-announce previously observed IDs.
        old = [a for a in prior.get('alerts',[]) if isinstance(a,dict)]
        seen = set()
        combined = []
        for alert in alerts + old:
            if alert.get('id') in seen: continue
            seen.add(alert.get('id'))
            combined.append(alert)
        combined = combined[:100]
        # Preserve IDs even if an old score disappears from the API.
        # Otherwise a later reappearance could create a duplicate alert.
        all_ids.update(known)
    else:
        combined = []  # Initial run is a quiet baseline.
    # Independent, permanent first-place history. Preserve every recorded gold event.
    # Bootstrap from previously observed gold medal alerts; never call baseline scores NEW.
    previous_records = json.loads(RECORDS.read_text(encoding='utf-8')) if RECORDS.exists() else {}
    history = [r for r in previous_records.get('records', []) if isinstance(r, dict)]
    gold_events = [a for a in combined if a.get('rank') == 1 and a.get('medal') == 'gold']
    seen_record_ids = {str(r.get('id')) for r in history}
    for event in gold_events:
        if str(event['id']) not in seen_record_ids:
            history.append({**event, 'record_type': 'new_first_place'})
            seen_record_ids.add(str(event['id']))
    # On first installation, if there is no historic gold event, retain a
    # clearly labeled current champion as a non-new fallback, avoiding an empty slide.
    if not history:
        candidates = [p for p in podium if p['rank'] == 1]
        if candidates:
            best = max(candidates, key=lambda p:(p['date'],p['id']))
            history.append({**best, 'record_type': 'baseline_champion'})
    history.sort(key=lambda r:(str(r.get('date','')), str(r.get('id',''))), reverse=True)
    RECORDS.write_text(json.dumps({'updated_at':result['updated_at'], 'records':history}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # Keep a durable ID set so records don't generate duplicate notifications.
    # Existing records are baseline on the very first run; later runs alert only
    # when a newly observed score currently holds a top-three game position.
    STATE.write_text(json.dumps({'known_ids':sorted(all_ids)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    FEED.write_text(json.dumps({'updated_at':result['updated_at'],'alerts':combined},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    update_daily_champion(result['champions'], result['updated_at'])
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Updated',result['total_games'],'games and',result['total_players'],'players')
if __name__=='__main__': main()

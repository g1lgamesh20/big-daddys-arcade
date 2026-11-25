#!/usr/bin/env python3
"""Read-only NEVER GIVE UP! evidence: five prior failed scores then observed Gold takeover.

Only immutable post-cutover approved submissions and observed takeover events
qualify. Earlier attempts must score strictly below the previous Gold record.
No awards, notifications, writes, or guesses from baseline holders.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from personal_best_preview import JOURNAL, ROOT, timestamp, CUTOFF
from gold_holder_history import HISTORY

def preview(journal, history):
    if (not isinstance(journal, dict) or journal.get('schema_version') != 1
            or journal.get('policy') != 'post_2026_11_19_approved_iscored_scores'
            or not isinstance(journal.get('scores'), dict)):
        raise ValueError('Invalid approved score journal')
    if (not isinstance(history, dict) or history.get('schema_version') != 1
            or history.get('policy') != 'observed_approved_snapshots_only'
            or not isinstance(history.get('transitions'), list)):
        raise ValueError('Invalid observed Gold history')
    scores = {}
    by_player_game = defaultdict(list)
    for sid, r in journal['scores'].items():
        if not isinstance(r, dict) or str(r.get('score_id')) != str(sid):
            raise ValueError('Invalid score evidence')
        player, game, score = r.get('name'), r.get('game'), r.get('score')
        if (not isinstance(player,str) or not player or player != player.strip().upper()
                or not isinstance(game,str) or not game.strip()
                or type(score) is not int or score < 0):
            raise ValueError('Invalid player, game, or score')
        submitted = timestamp(r['date'])
        observed = timestamp(r['first_observed_at'])
        if submitted < CUTOFF or submitted > observed:
            raise ValueError('Unsafe submission timestamps')
        item = {'id':str(sid), 'player':player, 'game_id':game,
                'score':score, 'submitted':submitted, 'observed':observed}
        scores[str(sid)] = item
        by_player_game[(player,game)].append(item)
    candidates = []
    seen_events = set()
    for event in history['transitions']:
        if not isinstance(event,dict) or not isinstance(event.get('id'),str) or event['id'] in seen_events:
            raise ValueError('Invalid or duplicate Gold transition')
        seen_events.add(event['id'])
        if event.get('type') not in ('takeover','tie_joined'):
            raise ValueError('Invalid Gold transition type')
        if event['type'] != 'takeover':
            continue
        gid = str(event.get('game_id',''))
        before, after = event.get('previous_score'), event.get('new_score')
        gained, winning_ids = event.get('gained_holders'), event.get('new_score_ids')
        if (type(before) is not int or type(after) is not int or before < 0 or after <= before
                or not isinstance(gained,list) or not isinstance(winning_ids,list)):
            raise ValueError('Malformed takeover evidence')
        observed_at = timestamp(event['observed_at'])
        for player in gained:
            if not isinstance(player,str) or not player or player != player.strip().upper():
                raise ValueError('Malformed gained holder')
            winners = [scores[str(sid)] for sid in winning_ids
                       if str(sid) in scores and scores[str(sid)]['player'] == player
                       and scores[str(sid)]['game_id'] == gid
                       and scores[str(sid)]['score'] == after
                       and scores[str(sid)]['observed'] <= observed_at]
            for winner in sorted(winners,key=lambda x:(x['submitted'],x['id'])):
                if winner['submitted'] > observed_at:
                    continue
                failed = sorted((r for r in by_player_game[(player,gid)]
                    if r['id'] != winner['id'] and r['submitted'] < winner['submitted']
                    and r['observed'] <= observed_at and r['score'] < before),
                    key=lambda x:(x['submitted'],x['id']))
                if len(failed) >= 5:
                    candidates.append({'id':'never_give_up:'+player,'player':player,
                        'game_id':gid,'game':event.get('game',''),
                        'gold_score_id':winner['id'],'gold_score':winner['score'],
                        'gold_transition_id':event['id'],
                        'prior_unsuccessful_score_ids':[x['id'] for x in failed],
                        'qualifying_attempts':len(failed),
                        'submitted_at':winner['submitted'].isoformat()})
                    break
    # Once per player lifetime, earliest evidenced Gold qualifies.
    earliest = {}
    for item in sorted(candidates,key=lambda x:(x['submitted_at'],x['gold_score_id'],x['game_id'])):
        earliest.setdefault(item['player'],item)
    return {'mode':'PREVIEW_ONLY_NO_AWARDS','approved_scores':len(scores),
            'observed_gold_transitions':len(seen_events),
            'candidates':sorted(earliest.values(),key=lambda x:x['player'])}

def main():
    journal=json.loads(JOURNAL.read_text(encoding='utf-8'))
    history=json.loads(HISTORY.read_text(encoding='utf-8'))
    report=preview(journal,history)
    print('NEVER GIVE UP! evidence preview (NO awards or pushes):',
          report['approved_scores'],'approved scores,',
          report['observed_gold_transitions'],'Gold transitions,',
          len(report['candidates']),'eligible players')
    for item in report['candidates']:
        print('  Candidate:',item['player'],item['game'],
              '5+ failed attempts before Gold score ID',item['gold_score_id'])

if __name__=='__main__':
    main()

#!/usr/bin/env python3
"""Record approved iScored Daily/Thursday participation by original submit time.

iScored developer Dan confirmed Nov 19, 2026:
- API score timestamps represent the original submission, not approval.
- Older timestamps may have been overwritten on approval before the bug fix.
- Offset-free timestamps use iScored's Central server local time.

This rollout deliberately begins with scores timestamped on/after Nov 20,
2026 00:00 Eastern. Earlier credits remain untouched, and no old scores are
retroactively reclassified. Only approved scores appear in this public feed.
No Monthly awards, Championship awards, score medals or pushes are issued.

This is a controlled cutover, not independently verified historical evidence.
A post-fix known submit-before-midnight/approve-after-midnight test remains
valuable for confirming the provider fix end-to-end.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from iscored_timestamp import parse_iscored_time
from generous_approval_credits import scheduled
from verify_challenge_award import issue_daily_milestones
from unified_milestone_awards import issue as issue_other_milestones

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'verified-challenge-awards.json'
REPORT = ROOT / 'submission-time-participation-report.json'
EASTERN = ZoneInfo('America/New_York')
CUTOVER = datetime(2026, 11, 20, 0, 0, tzinfo=EASTERN)
KINDS = ('daily', 'thursday')

def load(name, default):
    path = ROOT / name
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default

def event_end(day):
    # Date boundaries are Eastern local-midnight, even when DST changes.
    from datetime import date, timedelta
    return datetime.combine(date.fromisoformat(day) + timedelta(days=1),
                            datetime.min.time(), tzinfo=EASTERN)

def scan(rows, daily_archive, daily_live, thursday_state, ledger, now, enabled=False):
    """Return (next_ledger, aggregate_report, changed); pure and offline-testable."""
    if ledger.get('schema_version') != 1 or not isinstance(ledger.get('awards'), list) or not isinstance(ledger.get('verified_plays'), list):
        raise ValueError('Invalid permanent challenge ledger; refusing writes')
    if now.tzinfo is None:
        raise ValueError('now must include a timezone')
    now = now.astimezone(EASTERN)
    events = scheduled(daily_archive, daily_live, thursday_state, {})
    # Never use a sealed or unpublished monthly selection; MONTHLY is not in scope.
    available = {
        (kind, day): ev for (kind, day), ev in events.items()
        if kind in KINDS and isinstance(ev, dict) and ev.get('game_id')
    }
    existing = {
        (p.get('kind'), p.get('date'), str(p.get('player') or '').strip().upper())
        for p in ledger['verified_plays'] if isinstance(p, dict)
    }
    champion_types = {'daily': 'daily_champion', 'thursday': 'thursday_champion'}
    for award in ledger['awards']:
        if not isinstance(award, dict): continue
        kind = next((k for k, v in champion_types.items() if award.get('type') == v), None)
        if kind:
            existing.add((kind, award.get('date'), str(award.get('player') or '').strip().upper()))
    candidates = {}
    counters = {'parsed_approved_scores': 0, 'missing_or_bad_timestamps': 0,
                'pre_cutover_ignored': 0, 'future_timestamps_ignored': 0,
                'wrong_game_or_day': 0}
    for row in rows:
        if not isinstance(row, dict): continue
        gid = str(row.get('game') or '').strip()
        player = str(row.get('name') or '').strip().upper()[:48]
        sid = str(row.get('id') or '').strip()
        if not gid or not player or not sid: continue
        rawscore = row.get('score')
        if isinstance(rawscore, bool): continue
        try: score = int(rawscore)
        except (TypeError, ValueError): continue
        if score < 0: continue
        submitted = parse_iscored_time(row.get('date'))
        if submitted is None:
            counters['missing_or_bad_timestamps'] += 1
            continue
        counters['parsed_approved_scores'] += 1
        if submitted < CUTOVER:
            counters['pre_cutover_ignored'] += 1
            continue
        if submitted > now:
            counters['future_timestamps_ignored'] += 1
            continue
        day = submitted.date().isoformat()
        matched = False
        for kind in KINDS:
            event = available.get((kind, day))
            if not event or str(event['game_id']) != gid: continue
            if not datetime.combine(submitted.date(), datetime.min.time(), tzinfo=EASTERN) <= submitted < event_end(day):
                continue
            matched = True
            key = kind, day, player
            if key in existing:
                continue
            record = {'kind': kind, 'date': day, 'player': player,
                      'game_id': gid, 'game': str(event.get('game') or '')[:100],
                      'score': score, 'score_id': sid,
                      'original_submitted_at_et': submitted.isoformat()}
            previous = candidates.get(key)
            if previous is None or (score, -submitted.timestamp(), sid) > (
                previous['score'], -datetime.fromisoformat(previous['original_submitted_at_et']).timestamp(),
                previous['score_id']):
                candidates[key] = record
        if not matched:
            counters['wrong_game_or_day'] += 1
    proposed = [candidates[key] for key in sorted(candidates)]
    report = {
        'schema_version': 1,
        'mode': 'enabled' if enabled else 'preview',
        'policy': 'approved_public_score_original_submission_timestamp_within_Eastern_event_day',
        'score_date_timezone': 'America/Chicago when iScored omits explicit offset',
        'provider_fix_confirmed_on': '2026-11-19',
        'earliest_eligible_submission_et': CUTOVER.isoformat(),
        'historical_policy': 'Keep existing credits unchanged; never backfill pre-cutover records',
        'scope': ['daily_participation', 'thursday_participation'],
        'new_participation_credits': len(proposed),
        'new_daily_credits': sum(c['kind'] == 'daily' for c in proposed),
        'new_thursday_credits': sum(c['kind'] == 'thursday' for c in proposed),
        'no_championship_or_monthly_awards': True,
        'no_push_notifications': True,
        'counters': counters,
    }
    if not enabled or not proposed:
        return ledger, report, False
    result = json.loads(json.dumps(ledger))
    for c in proposed:
        item = {k: c[k] for k in ('kind', 'date', 'player', 'game_id', 'game', 'score', 'score_id')}
        item.update({
            'event_key': f"{c['kind']}:{c['date']}:{c['game_id']}:{c['player']}",
            'verified_at': now.isoformat(),
            'trophy_issued': False,
            'original_submitted_at_et': c['original_submitted_at_et'],
            'verification_method': 'iscored_developer_confirmed_original_submission_timestamp_post_fix',
        })
        result['verified_plays'].append(item)
    for player in sorted({c['player'] for c in proposed if c['kind'] == 'daily'}):
        issue_daily_milestones(result, player, now)
    issue_other_milestones(result, now)
    result['verified_plays'].sort(key=lambda r: (str(r.get('date') or ''), str(r.get('event_key') or '')))
    result['awards'].sort(key=lambda r: (str(r.get('date') or ''), str(r.get('id') or '')))
    return result, report, result != ledger

def main():
    from thursday_challenge import fetch
    now = datetime.now(timezone.utc)
    rows = fetch()
    ledger = load('verified-challenge-awards.json', {'schema_version': 1, 'awards': [], 'verified_plays': []})
    result, report, changed = scan(
        rows,
        load('daily-champion-history.json', {'days': []}),
        load('daily-champion.json', {'days': []}),
        load('thursday-challenge-state.json', {'weeks': {}}),
        ledger, now, enabled=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if changed:
        LEDGER.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Post-fix original-submission participation: new Daily', report['new_daily_credits'],
          '/ Thursday', report['new_thursday_credits'])
    print('No old credit changes, championship awards, monthly trophies, score medals, or pushes.')

if __name__ == '__main__': main()

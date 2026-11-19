#!/usr/bin/env python3
"""GitHub-only scoreboard refresh heartbeat and missed-slot diagnostics.

Runs only after a successful score download AND medal notification step.
The heartbeat is committed alongside the scoreboard. No polling service
or third-party scheduler is introduced. A missing GitHub schedule cannot
self-report until another job runs; stale timestamps expose that gap.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'refresh-health.json'
INTERVAL_MIN=30

def load(path=PATH):
    if not path.exists():return {'schema_version':1}
    data=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data,dict) or data.get('schema_version')!=1:
        raise ValueError('Invalid refresh-health.json; refusing to overwrite')
    return data

def parse_utc(value):
    if not isinstance(value,str):return None
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except ValueError:
        return None

def record(previous,now,trigger):
    if trigger not in ('schedule','workflow_dispatch'):
        raise ValueError('Unknown refresh trigger')
    now=now.astimezone(timezone.utc)
    stamp=now.isoformat()
    past=parse_utc(previous.get('last_success_at'))
    last_scheduled=parse_utc(previous.get('last_scheduled_success_at'))
    gap=round((now-past).total_seconds()/60,1) if past and now>=past else None
    # Measured lapse, not proof of individual dropped GitHub events.
    missed=max(0,int((now-past).total_seconds()//(INTERVAL_MIN*60))-1) if past and now>=past else None
    result={'schema_version':1,'target_interval_minutes':INTERVAL_MIN,
            'last_success_at':stamp,'last_trigger':trigger,
            'last_scheduled_success_at':stamp if trigger=='schedule' else
            (last_scheduled.isoformat() if last_scheduled else None),
            'previous_success_gap_minutes':gap,
            'estimated_missed_intervals_since_previous_success':missed,
            'monitoring_note':'Missing schedule events cannot create an alert by themselves. Check the age of last_success_at; only successful completed refreshes write this file.'}
    return result

def main():
    now=datetime.now(timezone.utc)
    trigger=os.getenv('GITHUB_EVENT_NAME','workflow_dispatch')
    previous=load()
    result=record(previous,now,trigger)
    PATH.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    age=result['previous_success_gap_minutes']
    print('Hall of Legends refresh succeeded via',trigger)
    print('Previous successful refresh gap (minutes):',age if age is not None else 'first monitored run')
    print('Estimated elapsed 30-minute slots without a successful refresh:',result['estimated_missed_intervals_since_previous_success'])
    if age is not None and age>65:
        print('WARNING: Scoreboard freshness gap exceeded 65 minutes. Inspect GitHub schedule history and iScored response.')
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a',encoding='utf-8') as stream:
            stream.write('## 👾 Hall of Legends refresh health\n')
            stream.write(f'- Successful refresh: **{now.isoformat()} UTC**\n')
            stream.write(f'- Trigger: **{trigger}**\n')
            stream.write(f'- Target: **every {INTERVAL_MIN} minutes**\n')
            stream.write(f'- Previous success gap: **{age if age is not None else "first monitored run"} minutes**\n')
            stream.write('- Monitoring limitation: scheduled jobs not created by GitHub cannot write their own alerts.\n')
            if age is not None and age>65:
                stream.write('- ⚠️ **Stale interval detected (>65 minutes).**\n')

if __name__=='__main__':main()

"""Offline regression checks for Medal Club: run python tools/test_medals.py."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import update_legends as mod


def payload(rows):
    return {'scores': [dict(id=i, name=p, game=1, gameName='Test Game', score=s, date=f'2026-11-04 12:{i:02d}:00') for i,p,s in rows]}


def run_case():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        with patch.object(mod, 'OUTPUT', root / 'legends.json'), patch.object(mod, 'STATE', root / 'medal-state.json'), patch.object(mod, 'FEED', root / 'medals.json'):
            current = payload([(1,'A',1000),(2,'B',900),(3,'C',800),(4,'D',700)])
            class Response:
                status = 200
                def __enter__(self): return self
                def __exit__(self,*args): return False
                def read(self,*args): return json.dumps(current).encode()
            with patch.object(mod, 'urlopen', return_value=Response()):
                mod.main()
                assert json.loads(mod.FEED.read_text())['alerts'] == [], 'First run must be quiet'
                current = payload([(1,'A',1000),(2,'B',900),(3,'C',800),(4,'D',700),(5,'E',850)])
                mod.main()
                alerts = json.loads(mod.FEED.read_text())['alerts']
                assert len(alerts)==1 and alerts[0]['id']=='5' and alerts[0]['medal']=='bronze', alerts
                mod.main()
                assert len(json.loads(mod.FEED.read_text())['alerts'])==1, 'No duplicate alerts'
                current = payload([(1,'A',1000),(2,'B',900),(3,'C',800),(4,'D',700),(5,'E',850),(6,'F',600)])
                mod.main()
                assert len(json.loads(mod.FEED.read_text())['alerts'])==1, 'Fourth or lower must not alert'
                # Temporarily missing score IDs must not be announced when restored.
                current = payload([(1,'A',1000),(2,'B',900),(3,'C',800),(4,'D',700),(6,'F',600)])
                mod.main()
                current = payload([(1,'A',1000),(2,'B',900),(3,'C',800),(4,'D',700),(5,'E',850),(6,'F',600)])
                mod.main()
                assert len(json.loads(mod.FEED.read_text())['alerts'])==1, 'Restored score must not alert twice'

if __name__=='__main__':
    run_case()
    print('Medal Club regression checks passed')

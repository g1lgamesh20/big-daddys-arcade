"""One shared exclusion list for monthly, Thursday, and daily selection."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def allowed_game_ids(ids):
    pool=json.loads((ROOT/'monthly-game-pool.json').read_text(encoding='utf-8'))
    excluded=pool.get('excluded_game_ids')
    if not isinstance(excluded,list):raise ValueError('Invalid game pool exclusions')
    return {str(i) for i in ids}-set(map(str,excluded))

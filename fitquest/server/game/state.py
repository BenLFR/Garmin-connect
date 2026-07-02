"""Tiny JSON persistence for the MVP (single player, single file).

A real deployment swaps this for a DB; the shape is the contract.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(os.environ.get(
    "FITQUEST_DATA", Path(__file__).resolve().parent.parent / "data"
))
STATE_FILE = DATA_DIR / "state.json"


def load() -> Optional[Dict[str, Any]]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None


def save(state: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def reset() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def streak_from_history(activities: List[Dict[str, Any]]) -> int:
    """Consecutive active days counted back from today/yesterday."""
    days = {a.get("startDate") for a in activities if a.get("startDate")}
    streak = 0
    cursor = date.today()
    if cursor.isoformat() not in days:
        cursor -= timedelta(days=1)  # grace: today not trained *yet*
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak

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


def active_days_by_week(activities: List[Dict[str, Any]],
                        weeks: int = 8) -> List[int]:
    """Distinct active days per COMPLETED ISO week, most recent first.
    The current (partial) week is excluded: it can't break a weekly streak
    before it is over — the streak model must absorb life's variance."""
    days = {a.get("startDate") for a in activities if a.get("startDate")}
    this_monday = date.today() - timedelta(days=date.today().weekday())
    out = []
    for w in range(1, weeks + 1):
        monday = this_monday - timedelta(weeks=w)
        count = sum(
            1 for d in range(7)
            if (monday + timedelta(days=d)).isoformat() in days
        )
        out.append(count)
    return out


def active_days_this_week(activities: List[Dict[str, Any]]) -> int:
    days = {a.get("startDate") for a in activities if a.get("startDate")}
    monday = date.today() - timedelta(days=date.today().weekday())
    return sum(1 for d in range(7)
               if (monday + timedelta(days=d)).isoformat() in days)

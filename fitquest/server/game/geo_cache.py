"""Persistent hex cache for the world map (separate from state.json).

Only hexes are stored, never raw polylines: ~30 bytes per hex keeps
years of exploration under a megabyte, and the Garmin details endpoint
is hit at most once per activity — failures are remembered as noGps so
nothing is ever re-fetched (rate-limit safety).

Shape:
{
  "origin": {"lat": .., "lon": ..} | null,
  "activities": {"<id>": {"hexes": [[q, r], ...], "date": "YYYY-MM-DD"}
                 | {"noGps": true}},
  "hexes": {"q,r": {"visits": n, "firstDate": "...", "lastDate": "..."}}
}
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from . import quests
from .state import DATA_DIR

GEO_FILE = DATA_DIR / "geo_cache.json"

# v2 added simplified display tracks ("points") per activity. Older caches
# lack them: cheapest correct migration is a rebuild — the capped backfill
# re-ingests everything within a couple of map opens.
CACHE_VERSION = 2


def _empty() -> Dict[str, Any]:
    return {"version": CACHE_VERSION, "origin": None,
            "activities": {}, "hexes": {}}


def load() -> Dict[str, Any]:
    if GEO_FILE.exists():
        cache = json.loads(GEO_FILE.read_text())
        if cache.get("version") == CACHE_VERSION:
            return cache
    return _empty()


def save(cache: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GEO_FILE.write_text(json.dumps(cache, ensure_ascii=False))


def reset() -> None:
    if GEO_FILE.exists():
        GEO_FILE.unlink()


def has_activity(cache: Dict[str, Any], activity_id: Any) -> bool:
    return str(activity_id) in cache["activities"]


def mark_no_gps(cache: Dict[str, Any], activity_id: Any) -> None:
    cache["activities"].setdefault(str(activity_id), {"noGps": True})


def record_hexes(cache: Dict[str, Any], activity_id: Any,
                 hexes: List[Tuple[int, int]], date: str,
                 points: Optional[List[Tuple[float, float]]] = None,
                 name: str = "") -> None:
    """Idempotent: an already-ingested activity is never double-counted.
    `points` is the simplified (lat, lon) display track, when available."""
    key = str(activity_id)
    if key in cache["activities"]:
        return
    cache["activities"][key] = {"hexes": [list(h) for h in hexes],
                                "date": date, "name": name,
                                "points": [list(p) for p in (points or [])]}
    distinct = {tuple(h) for h in hexes}
    for q, r in distinct:
        hkey = f"{q},{r}"
        cell = cache["hexes"].get(hkey)
        if cell is None:
            cache["hexes"][hkey] = {"visits": 1, "firstDate": date,
                                    "lastDate": date}
        else:
            cell["visits"] += 1
            cell["firstDate"] = min(cell["firstDate"], date)
            cell["lastDate"] = max(cell["lastDate"], date)


def new_hexes_in_week(cache: Dict[str, Any], wk: str) -> int:
    """Hexes whose first-ever visit falls in ISO week `wk`."""
    count = 0
    for cell in cache["hexes"].values():
        try:
            from datetime import date as _date

            if quests.week_key(_date.fromisoformat(cell["firstDate"])) == wk:
                count += 1
        except (KeyError, ValueError):
            continue
    return count


def player_hex(cache: Dict[str, Any]) -> Optional[Dict[str, int]]:
    """Last hex of the most recent tracked activity."""
    best = None
    for entry in cache["activities"].values():
        if "hexes" not in entry or not entry["hexes"]:
            continue
        if best is None or entry.get("date", "") > best.get("date", ""):
            best = entry
    if best is None:
        return None
    q, r = best["hexes"][-1]
    return {"q": q, "r": r}

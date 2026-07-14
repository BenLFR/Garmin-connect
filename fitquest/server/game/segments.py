"""Segments — quest-able routes built from the player's OWN past tracks.

A segment is a past outdoor route worth re-running. Completion is
hex-based, not time-based: re-covering ≥80 % of a segment's hexes in a
single activity counts as running it again. Times are deliberately NOT
the objective (SCIENCE.md: chasing a clock is an outcome goal → trophy
territory, never XP); the rewarded behaviour is the process of getting
back out on a known route.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from . import quests

MIN_HEXES = 6          # ≈ 1.5 km of distinct territory: too short = no quest
DEDUPE_OVERLAP = 0.7   # two tracks sharing >70 % of hexes are the same route
COMPLETE_COVERAGE = 0.8


def _track_km(points: List[List[float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for (lat0, lon0), (lat1, lon1) in zip(points, points[1:]):
        dx = (lon1 - lon0) * 111_320.0 * math.cos(math.radians(lat0))
        dy = (lat1 - lat0) * 111_320.0
        total += math.hypot(dx, dy)
    return round(total / 1000, 1)


def build_segments(cache: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Distinct routes from the geo cache, most recent first."""
    candidates = []
    for act_id, entry in cache["activities"].items():
        hexes = {tuple(h) for h in entry.get("hexes", [])}
        if len(hexes) < MIN_HEXES:
            continue
        candidates.append({
            "id": f"seg_{act_id}",
            "sourceActivityId": act_id,
            "name": entry.get("name") or f"Itinéraire du {entry.get('date', '?')}",
            "date": entry.get("date", ""),
            "firstDate": entry.get("date", ""),  # oldest occurrence of the route
            "hexes": hexes,
            "points": entry.get("points", []),
            "distanceKm": _track_km(entry.get("points", [])),
        })
    candidates.sort(key=lambda s: s["date"], reverse=True)

    segments: List[Dict[str, Any]] = []
    for cand in candidates:  # dedupe: most recent run represents the route…
        dup = None
        for seg in segments:
            overlap = (len(cand["hexes"] & seg["hexes"])
                       / max(min(len(cand["hexes"]), len(seg["hexes"])), 1))
            if overlap > DEDUPE_OVERLAP:
                dup = seg
                break
        if dup is not None:
            # …but the route's age is its OLDEST run: that is what makes it
            # a "known itinerary" rather than a brand-new one.
            dup["firstDate"] = min(dup["firstDate"], cand["date"])
        else:
            segments.append(cand)
    return segments


def runs_this_week(cache: Dict[str, Any], segment: Dict[str, Any],
                   wk: str) -> bool:
    """True if the route is a KNOWN itinerary (older than this week) and
    some activity of ISO week `wk` covers ≥80 % of its hexes — i.e. the
    player got back out on it. A brand-new route never counts."""
    from datetime import date as _date

    try:
        if quests.week_key(_date.fromisoformat(segment["firstDate"])) == wk:
            return False  # first ever run this week: new route, not a re-run
    except ValueError:
        return False
    for entry in cache["activities"].values():
        date = entry.get("date", "")
        try:
            if quests.week_key(_date.fromisoformat(date)) != wk:
                continue
        except ValueError:
            continue
        covered = {tuple(h) for h in entry.get("hexes", [])} & segment["hexes"]
        if len(covered) / len(segment["hexes"]) >= COMPLETE_COVERAGE:
            return True
    return False


def completed_this_week(cache: Dict[str, Any],
                        segments: List[Dict[str, Any]], wk: str) -> int:
    return sum(1 for seg in segments if runs_this_week(cache, seg, wk))


def payload(cache: Dict[str, Any], wk: str) -> List[Dict[str, Any]]:
    """Map-facing shape: geometry + this-week completion state."""
    out = []
    for seg in build_segments(cache):
        out.append({
            "id": seg["id"],
            "name": seg["name"],
            "date": seg["date"],
            "distanceKm": seg["distanceKm"],
            "points": seg["points"],
            "doneThisWeek": runs_this_week(cache, seg, wk),
        })
    return out

"""Demo data provider: a believable 4-week Garmin-like history.

Lets the whole game loop run without a Garmin account (onboarding pattern
"try before signup"). Shapes mirror what garmin_provider produces.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any, Dict, List

_TYPES = [
    # (activityType, name, load range, duration min range, elevation range)
    ("running", "Course matinale", (60, 140), (30, 70), (10, 80)),
    ("trail_running", "Trail en forêt", (120, 220), (60, 150), (250, 900)),
    ("cycling", "Sortie vélo", (90, 200), (60, 180), (100, 600)),
    ("strength_training", "Séance muscu", (40, 90), (30, 60), (0, 0)),
    ("hiit", "HIIT du soir", (80, 150), (20, 40), (0, 0)),
    ("hiking", "Randonnée", (70, 130), (90, 240), (300, 800)),
    ("lap_swimming", "Natation", (50, 110), (30, 60), (0, 0)),
]


def _seeded(seed: int = 42) -> random.Random:
    return random.Random(seed)


def generate_history(weeks: int = 4, seed: int = 42) -> List[Dict[str, Any]]:
    """~4-5 activities/week, most recent first."""
    rng = _seeded(seed)
    today = date.today()
    acts: List[Dict[str, Any]] = []
    act_id = 1000
    for day_offset in range(weeks * 7, 0, -1):
        d = today - timedelta(days=day_offset)
        if rng.random() > 0.62:  # ~4.6 sessions / week
            continue
        a_type, name, loads, durs, elevs = rng.choice(_TYPES)
        load = rng.uniform(*loads)
        acts.append({
            "activityId": act_id,
            "activityType": a_type,
            "activityName": name,
            "startDate": d.isoformat(),
            "durationMinutes": round(rng.uniform(*durs)),
            "trainingLoad": round(load, 1),
            "elevationGain": round(rng.uniform(*elevs)),
            "aerobicTE": round(min(5.0, load / 45), 1),
            "anaerobicTE": round(min(5.0, load / 90), 1)
            if a_type in ("hiit", "strength_training") else round(min(2.0, load / 150), 1),
            "isPR": False,
        })
        act_id += 1
    # sprinkle a couple of PRs like a normal progressing human
    if len(acts) >= 6:
        acts[-2]["isPR"] = True
        acts[len(acts) // 2]["isPR"] = True
    acts.reverse()  # most recent first
    return acts


def simulate_new_activity(rng_seed: int | None = None) -> Dict[str, Any]:
    """One fresh session for the demo 'Simuler une séance' CTA."""
    rng = random.Random(rng_seed)
    a_type, name, loads, durs, elevs = rng.choice(_TYPES)
    load = rng.uniform(*loads)
    return {
        "activityId": rng.randint(10_000, 99_999),
        "activityType": a_type,
        "activityName": name,
        "startDate": date.today().isoformat(),
        "durationMinutes": round(rng.uniform(*durs)),
        "trainingLoad": round(load, 1),
        "elevationGain": round(rng.uniform(*elevs)),
        "aerobicTE": round(min(5.0, load / 45), 1),
        "anaerobicTE": round(min(5.0, load / 90), 1),
        "isPR": rng.random() < 0.18,
    }


def lnrmssd_series(days: int = 70, seed: int = 42) -> List[float]:
    """Deterministic daily LnRMSSD series (oldest first) for the SWC
    methodology: stable baseline ~ln(65 ms) with physiological noise."""
    rng = _seeded(seed)
    base = 4.17  # ln(~65 ms)
    series = []
    for i in range(days):
        # slow drift + daily noise, deterministic across calls
        drift = 0.06 * (i / days)
        series.append(round(base + drift + rng.gauss(0, 0.12), 3))
    return series


def demo_wellness(seed: int = 42) -> Dict[str, Any]:
    """Daily wellness snapshot. Readiness is derived upstream from the SWC
    status (engine.readiness_from_swc), not invented here."""
    rng = _seeded(seed + date.today().toordinal())
    return {
        "hrvStatusScore": rng.randint(60, 95),
        "sleepScore": rng.randint(62, 94),
        "bodyBattery": rng.randint(50, 95),
    }


def demo_metrics(history: List[Dict[str, Any]], wellness: Dict[str, Any],
                 week_streak: int) -> Dict[str, Any]:
    """Aggregate history into the character_sheet() input metrics."""
    weekly_min = sum(a["durationMinutes"] for a in history
                     if a["activityType"] not in ("strength_training", "hiit")) / 4
    strength_load = sum(a["trainingLoad"] for a in history
                        if a["activityType"] in ("strength_training", "hiit"))
    active_days = len({a["startDate"] for a in history}) / 4
    return {
        "enduranceScore": 5200,
        "weeklyAerobicMinutes": weekly_min,
        "vo2max": 46,
        "maxPower": 620,
        "strengthLoad4w": strength_load,
        "anaerobicTE": max((a["anaerobicTE"] for a in history), default=0),
        "hrvStatusScore": wellness["hrvStatusScore"],
        "sleepScore": wellness["sleepScore"],
        "readiness": wellness.get("readiness", 65),
        "weekStreak": week_streak,
        "activeDaysPerWeek": active_days,
    }

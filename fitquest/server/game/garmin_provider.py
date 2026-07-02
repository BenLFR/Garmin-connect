"""Real-data provider backed by the `garminconnect` library (this repo).

Maps Garmin Connect responses onto the same activity/wellness shapes the
demo provider emits, so the engine and API never care which source runs.

Requires prior authentication (tokens in GARMINTOKENS / ~/.garminconnect,
created e.g. with the repo's example.py). Network + a real account needed:
this module is exercised manually, not in CI.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

# The garminconnect package lives at the repo root (not pip-installed in dev)
_REPO_ROOT = str(Path(__file__).resolve().parents[3])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Type keys we normalise Garmin's typeKey values into (engine vocabulary)
_TYPE_MAP = {
    "running": "running",
    "street_running": "running",
    "treadmill_running": "running",
    "track_running": "track_running",
    "trail_running": "trail_running",
    "cycling": "cycling",
    "road_biking": "cycling",
    "gravel_cycling": "gravel_cycling",
    "mountain_biking": "mountain_biking",
    "indoor_cycling": "indoor_cycling",
    "virtual_ride": "indoor_cycling",
    "lap_swimming": "lap_swimming",
    "open_water_swimming": "open_water_swimming",
    "strength_training": "strength_training",
    "indoor_cardio": "indoor_cardio",
    "hiit": "hiit",
    "hiking": "hiking",
    "walking": "walking",
    "stair_climbing": "stair_climbing",
    "mountaineering": "mountaineering",
}


def _norm_type(raw: Dict[str, Any]) -> str:
    key = ((raw.get("activityType") or {}).get("typeKey") or "").lower()
    return _TYPE_MAP.get(key, key or "other")


class GarminProvider:
    def __init__(self, tokenstore: str | None = None) -> None:
        import os

        from garminconnect import Garmin  # local package, lazy import

        self.api = Garmin()
        self.api.login(tokenstore or os.getenv("GARMINTOKENS", "~/.garminconnect"))

    # -- history ------------------------------------------------------------

    def history(self, weeks: int = 4) -> List[Dict[str, Any]]:
        end = date.today()
        start = end - timedelta(weeks=weeks)
        raw = self.api.get_activities_by_date(
            start.isoformat(), end.isoformat()
        )
        acts: List[Dict[str, Any]] = []
        for a in raw:
            acts.append({
                "activityId": a.get("activityId"),
                "activityType": _norm_type(a),
                "activityName": a.get("activityName") or "Activité",
                "startDate": (a.get("startTimeLocal") or "")[:10],
                "durationMinutes": round((a.get("duration") or 0) / 60),
                "trainingLoad": float(a.get("activityTrainingLoad") or 0),
                "elevationGain": float(a.get("elevationGain") or 0),
                "aerobicTE": float(a.get("aerobicTrainingEffect") or 0),
                "anaerobicTE": float(a.get("anaerobicTrainingEffect") or 0),
                "isPR": bool(a.get("pr") or False),
            })
        return acts

    # -- wellness -----------------------------------------------------------

    def wellness(self) -> Dict[str, Any]:
        today = date.today().isoformat()
        readiness = None
        try:
            tr = self.api.get_training_readiness(today)
            if isinstance(tr, list) and tr:
                readiness = tr[0].get("score")
            elif isinstance(tr, dict):
                readiness = tr.get("score")
        except Exception:
            pass
        sleep_score = None
        try:
            sleep = self.api.get_sleep_data(today)
            sleep_score = (
                (sleep.get("dailySleepDTO") or {})
                .get("sleepScores", {})
                .get("overall", {})
                .get("value")
            )
        except Exception:
            pass
        hrv = None
        try:
            hrv_data = self.api.get_hrv_data(today)
            status = ((hrv_data or {}).get("hrvSummary") or {}).get("status")
            hrv = {"BALANCED": 85, "UNBALANCED": 55, "LOW": 35}.get(status)
        except Exception:
            pass
        return {
            "readiness": readiness if readiness is not None else 70,
            "hrvStatusScore": hrv if hrv is not None else 70,
            "sleepScore": sleep_score if sleep_score is not None else 70,
            "bodyBattery": 70,
        }

"""Strava-backed provider — same activity/wellness contract as the
Garmin provider, so the engine never cares which source runs.

Metric caveats (documented, deliberate):
- trainingLoad: Strava has no Firstbeat load. We use Relative Effort
  (suffer_score, HR-based TRIMP-like, present when the athlete recorded
  HR) and otherwise fall back to a duration x heart-rate-ratio proxy
  (or duration alone). Same spirit, coarser resolution — every consumer
  of load (boss damage, spike cap) already tolerates that.
- aerobicTE/anaerobicTE: proxied from the load with the demo provider's
  heuristics — good enough for the intensity-budget classification.
- wellness: Strava exposes no HRV/sleep/readiness → neutral defaults
  (the SWC vitality features stay Garmin-only for now).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from . import geo, strava_auth

API = "https://www.strava.com/api/v3"

# Strava sport_type → engine vocabulary
_TYPE_MAP = {
    "Run": "running",
    "TrailRun": "trail_running",
    "VirtualRun": "running",
    "Ride": "cycling",
    "GravelRide": "gravel_cycling",
    "MountainBikeRide": "mountain_biking",
    "VirtualRide": "indoor_cycling",
    "EBikeRide": "cycling",
    "Swim": "lap_swimming",
    "OpenWaterSwim": "open_water_swimming",
    "WeightTraining": "strength_training",
    "Crossfit": "crossfit",
    "HighIntensityIntervalTraining": "hiit",
    "Workout": "indoor_cardio",
    "Hike": "hiking",
    "Walk": "walking",
    "StairStepper": "stair_climbing",
    "Snowshoe": "hiking",
    "AlpineSki": "other",
    "NordicSki": "other",
}

_INTENSE_TYPES = {"hiit", "strength_training", "crossfit"}


def _load_proxy(minutes: float, avg_hr: Optional[float],
                suffer_score: Optional[float]) -> float:
    """Best available training-load estimate for one activity."""
    if suffer_score:
        return float(suffer_score)
    if avg_hr:
        # crude TRIMP: minutes weighted by how hard the heart worked
        return round(minutes * max(avg_hr, 60) / 130, 1)
    return round(minutes * 0.8, 1)


def map_activity(a: Dict[str, Any]) -> Dict[str, Any]:
    """One Strava summary activity → the provider contract shape."""
    sport = a.get("sport_type") or a.get("type") or ""
    a_type = _TYPE_MAP.get(sport, "other")
    minutes = round((a.get("moving_time") or 0) / 60)
    load = _load_proxy(minutes, a.get("average_heartrate"),
                       a.get("suffer_score"))
    # TE proxies mirror demo_data's heuristics (validated for the budget)
    anaerobic_div = 90 if a_type in _INTENSE_TYPES else 150
    start = a.get("start_latlng") or [None, None]
    return {
        "activityId": a.get("id"),
        "activityType": a_type,
        "activityName": a.get("name") or "Activité",
        "startDate": (a.get("start_date_local") or "")[:10],
        "durationMinutes": minutes,
        "trainingLoad": load,
        "elevationGain": float(a.get("total_elevation_gain") or 0),
        "aerobicTE": round(min(5.0, load / 45), 1),
        "anaerobicTE": round(min(5.0, load / anaerobic_div), 1),
        "isPR": bool(a.get("pr_count")),
        "startLatitude": start[0],
        "startLongitude": start[1],
        "hasPolyline": bool((a.get("map") or {}).get("summary_polyline")),
    }


class StravaProvider:
    def __init__(self) -> None:
        self.token = strava_auth.access_token()

    def _get(self, path: str, **params: Any) -> Any:
        import requests

        resp = requests.get(
            f"{API}{path}", params=params,
            headers={"Authorization": f"Bearer {self.token}"}, timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    # -- history --------------------------------------------------------------

    def history(self, weeks: int = 4) -> List[Dict[str, Any]]:
        after = datetime.now(timezone.utc) - timedelta(weeks=weeks)
        raw = self._get("/athlete/activities",
                        after=int(after.timestamp()), per_page=100)
        acts = [map_activity(a) for a in raw]
        acts.sort(key=lambda a: a["startDate"], reverse=True)
        return acts

    def activity_polyline(self, activity_id: Any) -> Optional[List[tuple]]:
        """Full track of one activity (detail call → map.polyline),
        falling back to the summary polyline. Same one-shot contract as
        the Garmin provider: the geo cache remembers every outcome."""
        detail = self._get(f"/activities/{activity_id}")
        m = detail.get("map") or {}
        encoded = m.get("polyline") or m.get("summary_polyline")
        if encoded:
            return geo.decode_polyline(encoded)
        return None

    # -- wellness ---------------------------------------------------------------

    def wellness(self) -> Dict[str, Any]:
        # No HRV/sleep/readiness on the Strava API: neutral state.
        return {"readiness": 70, "hrvStatusScore": 70,
                "sleepScore": 70, "bodyBattery": 70}

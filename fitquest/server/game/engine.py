"""FitQuest game engine — v2, science-based.

Every mechanic here was audited against the literature; see
docs/AUDIT_SCIENTIFIQUE.md and SCIENCE.md for sources. Key rulings applied:

- XP rewards the PROCESS (time on feet, week structure), not raw metabolic
  load: process goals outperform outcome goals (d=1.36 vs 0.09, meta-analysis)
  and raw-load XP incentivises overtraining.
- Personal records earn a trophy, NOT XP (XP on PRs pushes unplanned
  max efforts).
- Weekly intensity distribution is enforced pyramidally: past ~20 % of weekly
  minutes at high intensity, further intense work earns discounted XP
  (HIIT dose should stay ≈20 % of volume; Casado 2022, Stöggl & Sperlich).
- Streaks are WEEKLY, not daily: tendon/bone remodelling needs 1-2 rest
  days/week, and daily streaks trigger the Abstinence Violation Effect on
  rupture (Marlatt & Gordon). A "successful week" = 3-5 active days.
  Compliant rest days earn recovery XP: rest is a play action.
- Boss fights are multi-session raids capped by the anti-spike rule: a single
  session's damage counts only up to 110 % of the biggest session of the last
  30 days (single-session spikes raise injury risk 52-64 %, Frandsen BJSM
  2025, n=5200). Boss HP targets ~100 % of a typical week, not a stretch.
- Vitality follows the Smallest Worthwhile Change methodology: 7-day rolling
  LnRMSSD vs a 60-day baseline ± 0.5 SD (Plews & Buchheit; HRV-guided
  training beats fixed plans, Manresa-Rocamora 2021).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Classes (unchanged: identity/SDT-competence layer, not an intensity driver)
# ---------------------------------------------------------------------------

CLASSES: Dict[str, Dict[str, Any]] = {
    "rodeur": {
        "name": "Rôdeur",
        "archetype": "Endurance",
        "tagline": "Le marathonien infatigable",
        "color": "#3ee6c1",
        "activity_types": {
            "running", "trail_running", "cycling", "gravel_cycling",
            "open_water_swimming", "lap_swimming", "hiking", "walking",
        },
        "favors": "volume aérobie & longues sorties",
    },
    "assassin": {
        "name": "Assassin",
        "archetype": "Sprint",
        "tagline": "Explosif, létal sur la courte",
        "color": "#ff4d8f",
        "activity_types": {
            "track_running", "sprint", "hiit", "indoor_cycling", "interval",
        },
        "favors": "intervalles & pics d'intensité",
    },
    "guerrier": {
        "name": "Guerrier",
        "archetype": "Force",
        "tagline": "Le tank",
        "color": "#ffb347",
        "activity_types": {
            "strength_training", "indoor_cardio", "crossfit", "functional",
        },
        "favors": "musculation & charge",
    },
    "paladin": {
        "name": "Paladin",
        "archetype": "Grimpeur",
        "tagline": "Dompteur de montagnes",
        "color": "#8f7bff",
        "activity_types": {
            "mountaineering", "trail_running", "hiking", "stair_climbing",
            "mountain_biking",
        },
        "favors": "dénivelé & côtes",
    },
    "voyageur": {
        "name": "Voyageur",
        "archetype": "Explorateur",
        "tagline": "Le nomade",
        "color": "#ffd166",
        "activity_types": set(),
        "favors": "variété d'activités & découverte",
    },
}

CLASS_MULTIPLIER = 1.5

# -- XP v2 (process-based) ---------------------------------------------------

XP_PER_MINUTE = 2.0          # Z1 pays like Z3: per-minute, intensity-agnostic
WEEK_STREAK_STEP = 0.05      # +5 % per consecutive successful week
WEEK_STREAK_CAP = 4          # capped at +20 %
INTENSE_SHARE_TARGET = 0.20  # pyramidal/polarized: ≤20 % of minutes intense
TID_DISCOUNT = 0.6           # intense work beyond the 20 % budget pays less
RECOVERY_XP = 40             # a compliant rest day is a play action
ANAEROBIC_TE_INTENSE = 2.0   # anaerobicTE ≥ 2.0 ⇒ session counts as intense

# Weekly pattern ruled healthy by the audit: 3-5 active days + rest days
HEALTHY_WEEK_MIN_DAYS = 3
HEALTHY_WEEK_MAX_DAYS = 5


@dataclass
class XPBreakdown:
    """Transparent breakdown shown in the Journal screen."""

    base_minutes: float
    class_multiplier: float
    week_streak_multiplier: float
    readiness_cap: float
    tid_factor: float
    xp: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "baseMinutes": round(self.base_minutes, 1),
            "classMultiplier": self.class_multiplier,
            "weekStreakMultiplier": round(self.week_streak_multiplier, 2),
            "readinessCap": self.readiness_cap,
            "tidFactor": self.tid_factor,
            "xp": self.xp,
        }


def readiness_cap(readiness: Optional[float]) -> float:
    """Anti-overtraining cap (kept from v1, validated by the audit's
    HRV/sleep findings; thresholds now fed by SWC status where available)."""
    if readiness is None:
        return 1.0
    if readiness < 25:
        return 0.3
    if readiness < 50:
        return 0.7
    return 1.0


def week_streak_multiplier(successful_weeks: int) -> float:
    return 1.0 + min(max(successful_weeks, 0), WEEK_STREAK_CAP) * WEEK_STREAK_STEP


def is_intense(activity: Dict[str, Any]) -> bool:
    return float(activity.get("anaerobicTE", 0) or 0) >= ANAEROBIC_TE_INTENSE


def tid_factor(activity: Dict[str, Any],
               week_activities: List[Dict[str, Any]]) -> float:
    """Weekly intensity-distribution guardrail.

    If this session is intense AND the week's intense share (this session
    included) already exceeds the ~20 % budget, its XP is discounted — the
    game stops paying full price for grinding intensity.
    """
    if not is_intense(activity):
        return 1.0
    total = sum(a.get("durationMinutes", 0) for a in week_activities) \
        + activity.get("durationMinutes", 0)
    intense = sum(a.get("durationMinutes", 0) for a in week_activities
                  if is_intense(a)) + activity.get("durationMinutes", 0)
    if total <= 0:
        return 1.0
    return TID_DISCOUNT if intense / total > INTENSE_SHARE_TARGET else 1.0


def intensity_budget(week_activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Weekly intensity budget vs the ~20 % pyramidal target — the player-
    facing view of the tid_factor guardrail (same inputs, no discount)."""
    total = sum(a.get("durationMinutes", 0) or 0 for a in week_activities)
    intense = sum(a.get("durationMinutes", 0) or 0 for a in week_activities
                  if is_intense(a))
    return {
        "intenseMinutes": round(intense),
        "totalMinutes": round(total),
        "budgetMinutes": round(total * INTENSE_SHARE_TARGET),
        "share": round(intense / total, 3) if total else 0.0,
        "target": INTENSE_SHARE_TARGET,
        "over": total > 0 and intense / total > INTENSE_SHARE_TARGET,
    }


def matches_class(player_class: str, activity_type: str,
                  is_new_activity_type: bool = False) -> bool:
    cls = CLASSES.get(player_class)
    if cls is None:
        return False
    if player_class == "voyageur":
        return is_new_activity_type
    return activity_type in cls["activity_types"]


def xp_for_activity(
    activity: Dict[str, Any],
    player_class: str,
    week_activities: Optional[List[Dict[str, Any]]] = None,
    successful_weeks: int = 0,
    readiness: Optional[float] = None,
    is_new_activity_type: bool = False,
) -> XPBreakdown:
    """Process-based XP: minutes moved × identity × structure, capped by
    recovery state. No raw-load payout, no PR payout."""
    minutes = max(float(activity.get("durationMinutes", 0) or 0), 0.0)
    base = minutes * XP_PER_MINUTE
    m_class = (
        CLASS_MULTIPLIER
        if matches_class(player_class, activity.get("activityType", ""),
                         is_new_activity_type)
        else 1.0
    )
    m_week = week_streak_multiplier(successful_weeks)
    cap = readiness_cap(readiness)
    tid = tid_factor(activity, week_activities or [])
    xp = round(base * m_class * m_week * cap * tid)
    return XPBreakdown(minutes, m_class, m_week, cap, tid, xp)


# ---------------------------------------------------------------------------
# Weekly pattern & recovery XP
# ---------------------------------------------------------------------------


def is_successful_week(active_days: int) -> bool:
    """3-5 active days: enough stimulus, mandatory rest preserved.
    6-7 days is NOT successful — no rest means no tissue remodelling."""
    return HEALTHY_WEEK_MIN_DAYS <= active_days <= HEALTHY_WEEK_MAX_DAYS


def successful_week_streak(active_days_per_week: List[int]) -> int:
    """Consecutive successful weeks, most recent first."""
    streak = 0
    for days in active_days_per_week:
        if is_successful_week(days):
            streak += 1
        else:
            break
    return streak


def recovery_xp_for_rest_day(active_days_this_week: int) -> int:
    """A rest day taken after real training this week earns recovery XP —
    rest becomes a play action instead of a streak-breaker."""
    return RECOVERY_XP if active_days_this_week >= 1 else 0


# ---------------------------------------------------------------------------
# Vitality — SWC methodology (LnRMSSD 7-day rolling vs 60-day baseline)
# ---------------------------------------------------------------------------


def vitality_swc(lnrmssd_daily: List[float]) -> Dict[str, Any]:
    """Smallest Worthwhile Change status from a daily LnRMSSD series
    (oldest first). Baseline = mean ± 0.5×SD over up to 60 days; trend =
    mean of last 7 days. Single-day values are too noisy to act on."""
    if len(lnrmssd_daily) < 10:
        return {"status": "normal", "trend": None, "low": None, "high": None}
    baseline = lnrmssd_daily[-60:]
    mean = statistics.fmean(baseline)
    sd = statistics.pstdev(baseline)
    swc = 0.5 * sd
    trend = statistics.fmean(lnrmssd_daily[-7:])
    low, high = mean - swc, mean + swc
    if trend < low:
        status = "debuff"    # parasympathetic suppression → prescribe Z1/rest
    elif trend > high:
        status = "buff"      # supercompensation → intense work authorised
    else:
        status = "normal"
    return {"status": status, "trend": round(trend, 3),
            "low": round(low, 3), "high": round(high, 3)}


def readiness_from_swc(status: str, sleep_score: Optional[float]) -> float:
    """Map SWC status (+ chronic sleep) onto the 0-100 readiness scale the
    XP cap consumes. Short sleep multiplies injury risk ~1.7× (Milewski)."""
    base = {"buff": 85.0, "normal": 65.0, "debuff": 35.0}.get(status, 65.0)
    if sleep_score is not None and sleep_score < 60:
        base -= 15.0
    return max(base, 0.0)


# ---------------------------------------------------------------------------
# Level curve (unchanged)
# ---------------------------------------------------------------------------


def xp_to_next(level: int) -> int:
    return round(100 * level ** 1.5)


def level_from_total_xp(total_xp: int) -> Dict[str, int]:
    level = 1
    remaining = max(total_xp, 0)
    while remaining >= xp_to_next(level):
        remaining -= xp_to_next(level)
        level += 1
    return {
        "level": level,
        "xpInLevel": remaining,
        "xpToNext": xp_to_next(level),
        "totalXp": max(total_xp, 0),
    }


# ---------------------------------------------------------------------------
# Class recommendation (unchanged)
# ---------------------------------------------------------------------------


def recommend_class(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    scores = {key: 0.0 for key in CLASSES}
    seen_types: set = set()
    for act in activities:
        a_type = act.get("activityType", "")
        load = max(float(act.get("trainingLoad", 0) or 0), 1.0)
        novelty = a_type not in seen_types
        seen_types.add(a_type)
        for key in CLASSES:
            if matches_class(key, a_type, is_new_activity_type=novelty):
                scores[key] += load * (0.4 if key == "voyageur" else 1.0)
        ascent = float(act.get("elevationGain", 0) or 0)
        if ascent > 200:
            scores["paladin"] += ascent / 10.0

    total = sum(scores.values()) or 1.0
    affinities = {k: round(100 * v / total) for k, v in scores.items()}
    best = max(affinities, key=lambda k: affinities[k])
    if affinities[best] == 0:
        best, affinities[best] = "voyageur", 100
    return {"recommended": best, "affinities": affinities}


# ---------------------------------------------------------------------------
# Character sheet (unchanged shape; VITALITÉ now SWC-driven upstream)
# ---------------------------------------------------------------------------


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def character_sheet(metrics: Dict[str, Any]) -> Dict[str, int]:
    stamina = _clamp(
        (float(metrics.get("enduranceScore", 0) or 0) / 9000) * 70
        + min(float(metrics.get("weeklyAerobicMinutes", 0) or 0) / 300, 1.0) * 30
    )
    force = _clamp(
        min(float(metrics.get("strengthLoad4w", 0) or 0) / 800, 1.0) * 60
        + (float(metrics.get("anaerobicTE", 0) or 0) / 5.0) * 40
    )
    agilite = _clamp(
        (float(metrics.get("vo2max", 0) or 0) / 60.0) * 70
        + min(float(metrics.get("maxPower", 0) or 0) / 900, 1.0) * 30
    )
    vitalite = _clamp(
        float(metrics.get("hrvStatusScore", 0) or 0) * 0.35
        + float(metrics.get("sleepScore", 0) or 0) * 0.35
        + float(metrics.get("readiness", 0) or 0) * 0.30
    )
    discipline = _clamp(
        min(float(metrics.get("weekStreak", 0) or 0) / 4, 1.0) * 50
        + min(float(metrics.get("activeDaysPerWeek", 0) or 0) / 4, 1.0) * 50
    )
    return {
        "stamina": stamina,
        "force": force,
        "agilite": agilite,
        "vitalite": vitalite,
        "discipline": discipline,
    }


# ---------------------------------------------------------------------------
# Boss — multi-session raid with the anti-spike damage cap
# ---------------------------------------------------------------------------

BOSS_NAMES = [
    "Golem des Contreforts", "Spectre du Bitume", "Hydre des Fractionnés",
    "Titan de Fonte", "Wyverne des Crêtes", "Liche du Canapé",
    "Béhémoth Brumeux", "Seigneur du Chrono",
]


@dataclass
class Boss:
    name: str
    level: int
    max_hp: int
    hp: int
    reward_xp: int
    lore: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "maxHp": self.max_hp,
            "hp": self.hp,
            "rewardXp": self.reward_xp,
            "lore": self.lore,
            "defeated": self.hp <= 0,
        }


def spawn_boss(player_level: int, avg_weekly_load: float) -> Boss:
    """Boss HP ≈ one typical week (×1.0, no stretch): the challenge is
    consistency across sessions, never a volume spike."""
    base = max(avg_weekly_load, 150.0)
    max_hp = round(base)
    name = BOSS_NAMES[(player_level - 1) % len(BOSS_NAMES)]
    return Boss(
        name=name,
        level=player_level,
        max_hp=max_hp,
        hp=max_hp,
        reward_xp=round(100 * player_level ** 1.2),
        lore=("Use-le à ta cadence habituelle : les dégâts d'une séance sont "
              "plafonnés — aucune séance héroïque ne peut le tuer d'un coup."),
    )


def anti_spike_cap(history: List[Dict[str, Any]],
                   days: int = 30) -> Optional[float]:
    """110 % of the biggest single-session load of the last `days` days.
    Damage beyond this cap never counts (Frandsen 2025: single-session
    spikes of +10-30 % raise injury risk 52-64 %)."""
    from datetime import date, timedelta

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    loads = [float(a.get("trainingLoad", 0) or 0)
             for a in history if a.get("startDate", "") >= cutoff]
    if not loads:
        return None
    return round(max(loads) * 1.10, 1)


def damage_boss(boss: Boss, training_load: float, vitalite: int,
                spike_cap: Optional[float] = None) -> Dict[str, Any]:
    """One session's damage. VITALITÉ scales it (rest matters); the
    anti-spike cap silently truncates heroic single sessions."""
    effective = max(training_load, 0.0)
    capped = False
    if spike_cap is not None and effective > spike_cap:
        effective = spike_cap
        capped = True
    scale = 0.75 + (max(0, min(100, vitalite)) / 100) * 0.5
    dmg = round(effective * scale)
    boss.hp = max(0, boss.hp - dmg)
    return {"damage": dmg, "capped": capped}

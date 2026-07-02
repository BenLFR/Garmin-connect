"""FitQuest game engine.

Implements the validated MVP loop: relative-effort XP, level curve,
class recommendation from activity history, and the 5-stat character sheet.
Every rule here mirrors GAME_DESIGN.md — keep both in sync.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

CLASSES: Dict[str, Dict[str, Any]] = {
    "rodeur": {
        "name": "Rôdeur",
        "archetype": "Endurance",
        "tagline": "Le marathonien infatigable",
        "color": "#3ee6c1",
        # Garmin activity type keys that earn the class multiplier
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
        "activity_types": set(),  # earns via variety, see xp_for_activity
        "favors": "variété d'activités & découverte",
    },
}

CLASS_MULTIPLIER = 1.5
STREAK_STEP = 0.05
STREAK_CAP_DAYS = 7
PR_BONUS = 200

# ---------------------------------------------------------------------------
# XP engine
# ---------------------------------------------------------------------------


@dataclass
class XPBreakdown:
    """Transparent breakdown shown in the Journal screen."""

    base_load: float
    class_multiplier: float
    streak_multiplier: float
    readiness_cap: float
    pr_bonus: int
    xp: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "baseLoad": round(self.base_load, 1),
            "classMultiplier": self.class_multiplier,
            "streakMultiplier": round(self.streak_multiplier, 2),
            "readinessCap": self.readiness_cap,
            "prBonus": self.pr_bonus,
            "xp": self.xp,
        }


def readiness_cap(readiness: Optional[float]) -> float:
    """Anti-overtraining cap. Red readiness nearly cuts XP off."""
    if readiness is None:
        return 1.0
    if readiness < 25:
        return 0.3
    if readiness < 50:
        return 0.7
    return 1.0


def streak_multiplier(streak_days: int) -> float:
    return 1.0 + min(max(streak_days, 0), STREAK_CAP_DAYS) * STREAK_STEP


def matches_class(player_class: str, activity_type: str,
                  is_new_activity_type: bool = False) -> bool:
    cls = CLASSES.get(player_class)
    if cls is None:
        return False
    if player_class == "voyageur":
        # The explorer is rewarded for novelty, not a fixed activity list.
        return is_new_activity_type
    return activity_type in cls["activity_types"]


def xp_for_activity(
    training_load: float,
    player_class: str,
    activity_type: str,
    streak_days: int = 0,
    readiness: Optional[float] = None,
    new_pr: bool = False,
    is_new_activity_type: bool = False,
) -> XPBreakdown:
    """The validated XP formula (GAME_DESIGN.md §3)."""
    base = max(training_load, 0.0)
    m_class = (
        CLASS_MULTIPLIER
        if matches_class(player_class, activity_type, is_new_activity_type)
        else 1.0
    )
    m_streak = streak_multiplier(streak_days)
    cap = readiness_cap(readiness)
    bonus = PR_BONUS if new_pr else 0
    xp = round(base * m_class * m_streak * cap) + bonus
    return XPBreakdown(base, m_class, m_streak, cap, bonus, xp)


# ---------------------------------------------------------------------------
# Level curve
# ---------------------------------------------------------------------------


def xp_to_next(level: int) -> int:
    """XP required to go from `level` to `level + 1`: 100 × n^1.5."""
    return round(100 * level ** 1.5)


def level_from_total_xp(total_xp: int) -> Dict[str, int]:
    """Resolve level + progress within level from lifetime XP."""
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
# Class recommendation (onboarding "révélation")
# ---------------------------------------------------------------------------


def recommend_class(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Score each class against the last-4-weeks history.

    Load-weighted so a big weekly long run counts more than a 10-min stroll.
    Returns affinity percentages for the S4 reveal screen.
    """
    scores = {key: 0.0 for key in CLASSES}
    seen_types: set = set()
    for act in activities:
        a_type = act.get("activityType", "")
        load = max(float(act.get("trainingLoad", 0) or 0), 1.0)
        novelty = a_type not in seen_types
        seen_types.add(a_type)
        for key in CLASSES:
            if matches_class(key, a_type, is_new_activity_type=novelty):
                # Novelty credit is discounted, otherwise a short history
                # (where everything is "new") hands the reco to the Voyageur.
                scores[key] += load * (0.4 if key == "voyageur" else 1.0)
        # Climbing signal: elevation feeds the Paladin even on generic types
        ascent = float(act.get("elevationGain", 0) or 0)
        if ascent > 200:
            scores["paladin"] += ascent / 10.0

    total = sum(scores.values()) or 1.0
    affinities = {k: round(100 * v / total) for k, v in scores.items()}
    best = max(affinities, key=lambda k: affinities[k])
    if affinities[best] == 0:
        best, affinities[best] = "voyageur", 100  # blank history → explorer
    return {"recommended": best, "affinities": affinities}


# ---------------------------------------------------------------------------
# Character sheet (5 stats, 0–100)
# ---------------------------------------------------------------------------


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def character_sheet(metrics: Dict[str, Any]) -> Dict[str, int]:
    """Map real Garmin-derived metrics onto the 5 RPG attributes.

    `metrics` keys (all optional, best-effort):
      enduranceScore (0-10000ish), weeklyAerobicMinutes, vo2max,
      maxPower, strengthLoad4w, anaerobicTE (0-5), hrvStatusScore (0-100),
      sleepScore (0-100), readiness (0-100), streakDays, activeDaysPerWeek
    """
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
        min(float(metrics.get("streakDays", 0) or 0) / 14, 1.0) * 50
        + min(float(metrics.get("activeDaysPerWeek", 0) or 0) / 5, 1.0) * 50
    )
    return {
        "stamina": stamina,
        "force": force,
        "agilite": agilite,
        "vitalite": vitalite,
        "discipline": discipline,
    }


# ---------------------------------------------------------------------------
# Boss of the current tier (MVP v1: weekly calibrated raid)
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
    """Boss HP is calibrated on the player's own recent weekly load:
    a stretch (~115 %) of a normal week, never an absolute wall."""
    base = max(avg_weekly_load, 150.0)
    max_hp = round(base * 1.15)
    name = BOSS_NAMES[(player_level - 1) % len(BOSS_NAMES)]
    return Boss(
        name=name,
        level=player_level,
        max_hp=max_hp,
        hp=max_hp,
        reward_xp=round(100 * player_level ** 1.2),
        lore="Inflige-lui des dégâts à chaque séance : ton Training Load est ton arme.",
    )


def damage_boss(boss: Boss, training_load: float, vitalite: int) -> int:
    """Damage dealt by one session. VITALITÉ scales damage (rest matters):
    50 vitalité = ×1.0, 100 = ×1.25, 0 = ×0.75."""
    scale = 0.75 + (max(0, min(100, vitalite)) / 100) * 0.5
    dmg = round(max(training_load, 0) * scale)
    boss.hp = max(0, boss.hp - dmg)
    return dmg

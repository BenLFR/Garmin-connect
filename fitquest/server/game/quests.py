"""Phase 2 — weekly quests, guild & world boss (GAME_DESIGN.md §7-8).

Weekly quests: 3 challenges, deterministic rotation every ISO week (lundi),
one of them flavored to the player's class. Progress is computed from the
current week's activities; rewards are granted at sync time.

Guild: in demo mode the party is simulated with NPC companions so the
world-boss loop (collective HP bar + diversity bonus) is playable solo.
The data shapes are the contract for the real multiplayer later.
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from . import engine

# ---------------------------------------------------------------------------
# Weekly quests
# ---------------------------------------------------------------------------

# Generic templates: (id, label, metric, target, reward_xp)
# metrics: sessions | load | long_session_min | pr
GENERIC_QUESTS = [
    ("g_sessions3", "Aventurier assidu — 3 séances cette semaine", "sessions", 3, 150),
    ("g_load400", "Forgeron de l'effort — 400 de load cumulé", "load", 400, 180),
    ("g_long60", "Longue traque — 1 séance de 60 min ou plus", "long_session_min", 60, 150),
    ("g_sessions4", "Infatigable — 4 séances cette semaine", "sessions", 4, 220),
    ("g_load550", "Marteau de guerre — 550 de load cumulé", "load", 550, 240),
    ("g_pr", "Gloire éternelle — bats un record personnel", "pr", 1, 250),
]

# Geo quests (world map): metric new_hexes = hexes first revealed this week.
# Appended as a 4th quest when the map has data — kept out of GENERIC_QUESTS
# so the historical Random(week_key) draws stay unchanged.
GEO_QUESTS = [
    ("q_geo5", "Cartographe — révèle 5 nouveaux hexagones", "new_hexes", 5, 200),
    ("q_geo10", "Grand arpenteur — révèle 10 nouveaux hexagones", "new_hexes", 10, 260),
]

# Segment quests join the geo pool once the player has re-runnable routes
# (metric segments_done, injected from the geo cache like new_hexes).
SEGMENT_QUESTS = [
    ("q_seg1", "Sur tes traces — reparcours un itinéraire connu", "segments_done", 1, 220),
]

# Class-flavored: metric class_minutes = minutes on class-matching activities
CLASS_QUESTS = {
    "rodeur": ("c_rodeur", "Sentier du Rôdeur — 120 min d'aérobie", "class_minutes", 120, 200),
    "assassin": ("c_assassin", "Contrat de l'Assassin — 40 min d'intensité", "class_minutes", 40, 200),
    "guerrier": ("c_guerrier", "Épreuve du Guerrier — 60 min de force", "class_minutes", 60, 200),
    "paladin": ("c_paladin", "Serment du Paladin — 90 min en montée", "class_minutes", 90, 200),
    "voyageur": ("c_voyageur", "Carnet du Voyageur — 2 types d'activités différents", "class_types", 2, 200),
}


def week_key(d: Optional[date] = None) -> str:
    d = d or date.today()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _week_bounds(d: Optional[date] = None) -> tuple[str, str]:
    d = d or date.today()
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat(), (monday + timedelta(days=6)).isoformat()


def weekly_quests(player_class: str, d: Optional[date] = None,
                  with_geo: bool = False,
                  with_segments: bool = False) -> List[Dict[str, Any]]:
    """3 quests: 2 generic (rotating deterministically) + 1 class quest,
    plus 1 geo quest when the world map has data (with_geo); the geo pool
    widens to segment quests once re-runnable routes exist."""
    rng = random.Random(week_key(d))
    generic = rng.sample(GENERIC_QUESTS, 2)
    cls = CLASS_QUESTS.get(player_class, CLASS_QUESTS["voyageur"])
    picked = [*generic, cls]
    if with_geo:
        pool = GEO_QUESTS + (SEGMENT_QUESTS if with_segments else [])
        picked.append(rng.choice(pool))
    out = []
    for qid, label, metric, target, reward in picked:
        out.append({"id": qid, "label": label, "metric": metric,
                    "target": target, "rewardXp": reward})
    return out


def quest_progress(quests: List[Dict[str, Any]], history: List[Dict[str, Any]],
                   player_class: str, d: Optional[date] = None,
                   extra_values: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
    """Annotate quests with current progress from this ISO week's activities.
    Metrics the history can't answer (e.g. new_hexes from the geo cache)
    are injected by the caller through extra_values."""
    start, end = _week_bounds(d)
    week_acts = [a for a in history if start <= a.get("startDate", "") <= end]
    class_acts = [a for a in week_acts
                  if engine.matches_class(player_class, a["activityType"])]
    values = {
        "sessions": len(week_acts),
        "load": round(sum(a["trainingLoad"] for a in week_acts)),
        "long_session_min": max((a["durationMinutes"] for a in week_acts), default=0),
        "pr": sum(1 for a in week_acts if a.get("isPR")),
        "class_minutes": sum(a["durationMinutes"] for a in class_acts),
        "class_types": len({a["activityType"] for a in week_acts}),
    }
    values.update(extra_values or {})
    out = []
    for q in quests:
        progress = min(values.get(q["metric"], 0), q["target"])
        out.append({**q, "progress": progress, "done": progress >= q["target"]})
    return out


# ---------------------------------------------------------------------------
# Guild & world boss (demo: NPC party simulation)
# ---------------------------------------------------------------------------

NPC_POOL = [
    ("Kaela", "assassin"), ("Bromm", "guerrier"), ("Sylvane", "rodeur"),
    ("Aldric", "paladin"), ("Nym", "voyageur"), ("Torvi", "guerrier"),
    ("Lyra", "assassin"), ("Fenn", "rodeur"),
]

WORLD_BOSS_NAMES = [
    "Dragon de la Sédentarité", "Kraken des Excuses", "Colosse du Lundi",
    "Hydre Hivernale", "Léviathan du Renoncement",
]


def diversity_bonus(classes: List[str]) -> float:
    """+5 % damage per distinct class beyond the first, capped at +20 %."""
    distinct = len(set(classes))
    return 1.0 + min(max(distinct - 1, 0), 4) * 0.05


def spawn_guild(player_class: str, seed: int = 7) -> Dict[str, Any]:
    """4 NPC companions picked to complement the player's class."""
    rng = random.Random(seed)
    pool = sorted(NPC_POOL, key=lambda n: (n[1] == player_class, rng.random()))
    members = [{"name": n, "class": c, "npc": True} for n, c in pool[:4]]
    return {"name": "Compagnie de l'Aube", "members": members}


def spawn_world_boss(avg_weekly_load: float, tier: int = 1) -> Dict[str, Any]:
    """Collective HP: a party of 5 each doing ~a normal week, scaled by tier."""
    base = max(avg_weekly_load, 150.0)
    max_hp = round(base * 5 * (1 + 0.25 * (tier - 1)))
    rng = random.Random(tier)
    return {
        "name": WORLD_BOSS_NAMES[(tier - 1) % len(WORLD_BOSS_NAMES)],
        "tier": tier,
        "maxHp": max_hp,
        "hp": max_hp,
        "rewardXp": 400 + 150 * (tier - 1),
        "weekKey": week_key(),
    }


def npc_daily_damage(guild: Dict[str, Any], days: int,
                     avg_weekly_load: float, seed: int) -> List[Dict[str, Any]]:
    """Each NPC trains ~4 days/week; damage ≈ a believable session load."""
    rng = random.Random(seed)
    hits = []
    session = max(avg_weekly_load / 4.5, 30.0)
    for _ in range(max(days, 0)):
        for m in guild["members"]:
            if rng.random() < 4.5 / 7:
                hits.append({
                    "name": m["name"],
                    "damage": round(session * rng.uniform(0.6, 1.4)),
                })
    return hits

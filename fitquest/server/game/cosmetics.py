"""Cosmetic loot — visual identity rewards (SDT competence display).

SCIENCE.md ruling: no reward may be indexed on raw training volume or
load (that would re-create the grinding incentive the XP engine was
rebuilt to avoid). Unlock conditions are LEVEL, BOSS KILLS, WORLD-BOSS
TIER and QUESTS CLAIMED only — all of them process/consistency proxies.

Slots:
- title: shown under the hero's name
- halo:  glow color around the sprite (overrides the class glow)
- gear:  16x16 pixel overlay rendered on top of the hero sprite
"""

from __future__ import annotations

from typing import Any, Dict, List

VALID_UNLOCKS = {"level", "bossKills", "worldBossTier", "questsClaimed"}
SLOTS = ("title", "halo", "gear")

ITEMS: List[Dict[str, Any]] = [
    # -- titles (level & quest milestones) -----------------------------------
    {"id": "t_novice", "slot": "title", "name": "Novice de la Taverne",
     "unlock": {"type": "level", "value": 2}},
    {"id": "t_eveille", "slot": "title", "name": "Éveillé",
     "unlock": {"type": "level", "value": 5}},
    {"id": "t_vaillant", "slot": "title", "name": "Vaillant",
     "unlock": {"type": "level", "value": 10}},
    {"id": "t_legende", "slot": "title", "name": "Légende locale",
     "unlock": {"type": "level", "value": 16}},
    {"id": "t_queteur", "slot": "title", "name": "Quêteur assermenté",
     "unlock": {"type": "questsClaimed", "value": 10}},
    # -- halos ----------------------------------------------------------------
    {"id": "h_teal", "slot": "halo", "name": "Halo d'aube", "color": "#3ee6c1",
     "unlock": {"type": "level", "value": 6}},
    {"id": "h_gold", "slot": "halo", "name": "Halo doré", "color": "#ffd166",
     "unlock": {"type": "level", "value": 12}},
    {"id": "h_crimson", "slot": "halo", "name": "Halo sanglant", "color": "#ff4d8f",
     "unlock": {"type": "bossKills", "value": 5}},
    # -- gear (pixel overlays, maps live in webapp/src/sprites.jsx) -----------
    {"id": "g_bandeau", "slot": "gear", "name": "Bandeau du disciple",
     "unlock": {"type": "level", "value": 4}},
    {"id": "g_epee", "slot": "gear", "name": "Épée du premier boss",
     "unlock": {"type": "bossKills", "value": 1}},
    {"id": "g_bouclier", "slot": "gear", "name": "Bouclier du triple",
     "unlock": {"type": "bossKills", "value": 3}},
    {"id": "g_couronne", "slot": "gear", "name": "Couronne du sommet",
     "unlock": {"type": "level", "value": 18}},
    {"id": "g_aile", "slot": "gear", "name": "Ailes de raid",
     "unlock": {"type": "worldBossTier", "value": 2}},
]

_BY_ID = {item["id"]: item for item in ITEMS}

UNLOCK_LABELS = {
    "level": "Niveau {value}",
    "bossKills": "{value} boss vaincu(s)",
    "worldBossTier": "Raid de palier {value}",
    "questsClaimed": "{value} quêtes accomplies",
}


def player_counters(st: Dict[str, Any], level: int) -> Dict[str, int]:
    return {
        "level": level,
        "bossKills": int(st.get("bossKills", 0)),
        "worldBossTier": int((st.get("worldBoss") or {}).get("tier", 1)),
        "questsClaimed": sum(len(v) for v in st.get("claimedQuests", {}).values()),
    }


def is_unlocked(item: Dict[str, Any], counters: Dict[str, int]) -> bool:
    unlock = item["unlock"]
    return counters.get(unlock["type"], 0) >= unlock["value"]


def unlocked_ids(counters: Dict[str, int]) -> List[str]:
    return [item["id"] for item in ITEMS if is_unlocked(item, counters)]


def get_item(item_id: str) -> Dict[str, Any] | None:
    return _BY_ID.get(item_id)


def payload(st: Dict[str, Any], level: int) -> Dict[str, Any]:
    counters = player_counters(st, level)
    items = []
    for item in ITEMS:
        unlock = item["unlock"]
        items.append({
            **item,
            "unlocked": is_unlocked(item, counters),
            "unlockLabel": UNLOCK_LABELS[unlock["type"]].format(value=unlock["value"]),
        })
    return {
        "items": items,
        "equipped": st.get("equipped", {slot: None for slot in SLOTS}),
        "counters": counters,
    }

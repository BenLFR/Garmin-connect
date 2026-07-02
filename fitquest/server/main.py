"""FitQuest API — FastAPI backend serving the game loop + the built webapp.

Run:  uvicorn main:app --port 8000   (from fitquest/server)
Demo mode needs no Garmin account; mode=garmin uses saved Garth tokens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from game import demo_data, engine, quests, state as store

app = FastAPI(title="FitQuest API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _provider_history(mode: str) -> List[Dict[str, Any]]:
    if mode == "garmin":
        from game.garmin_provider import GarminProvider

        return GarminProvider().history()
    return demo_data.generate_history()


def _provider_wellness(mode: str) -> Dict[str, Any]:
    if mode == "garmin":
        from game.garmin_provider import GarminProvider

        return GarminProvider().wellness()
    return demo_data.demo_wellness()


def _require_state() -> Dict[str, Any]:
    st = store.load()
    if st is None:
        raise HTTPException(status_code=409, detail="onboarding_required")
    if _ensure_phase2(st):
        store.save(st)
    return st


def _ensure_phase2(st: Dict[str, Any]) -> bool:
    """Lazy-init guild/world-boss/quest fields + apply NPC daily ticks.
    Returns True when the state was mutated (caller persists)."""
    from datetime import date

    changed = False
    if "guild" not in st:
        st["guild"] = quests.spawn_guild(st["class"])
        changed = True
    if "worldBoss" not in st:
        st["worldBoss"] = quests.spawn_world_boss(_avg_weekly_load(st["history"]))
        changed = True
    st.setdefault("claimedQuests", {})
    st.setdefault("guildLog", [])

    today = date.today().isoformat()
    last_tick = st.get("lastGuildTick")
    if last_tick != today:
        days = 1
        if last_tick:
            days = max((date.fromisoformat(today) - date.fromisoformat(last_tick)).days, 0)
        hits = quests.npc_daily_damage(
            st["guild"], days, _avg_weekly_load(st["history"]),
            seed=date.today().toordinal(),
        )
        bonus = quests.diversity_bonus(
            [st["class"]] + [m["class"] for m in st["guild"]["members"]]
        )
        wb = st["worldBoss"]
        for h in hits:
            dmg = round(h["damage"] * bonus)
            wb["hp"] = max(0, wb["hp"] - dmg)
            st["guildLog"] = ([{"name": h["name"], "damage": dmg, "date": today}]
                              + st["guildLog"])[:12]
        st["lastGuildTick"] = today
        changed = True
    return changed


def _avg_weekly_load(history: List[Dict[str, Any]]) -> float:
    return sum(a["trainingLoad"] for a in history) / 4 if history else 0.0


def _full_state_payload(st: Dict[str, Any]) -> Dict[str, Any]:
    wellness = _provider_wellness(st["mode"])
    metrics = demo_data.demo_metrics(st["history"], wellness, st["streakDays"])
    sheet = engine.character_sheet(metrics)
    level = engine.level_from_total_xp(st["totalXp"])
    cls = engine.CLASSES[st["class"]]
    return {
        "player": {
            "name": st["playerName"],
            "class": st["class"],
            "className": cls["name"],
            "classColor": cls["color"],
            "archetype": cls["archetype"],
            "mode": st["mode"],
        },
        "level": level,
        "streakDays": st["streakDays"],
        "wellness": wellness,
        "characterSheet": sheet,
        "boss": st["boss"],
        "prCount": sum(1 for a in st["history"] if a.get("isPR")),
        "quests": _quests_payload(st),
        "guild": {
            **st["guild"],
            "diversityBonus": quests.diversity_bonus(
                [st["class"]] + [m["class"] for m in st["guild"]["members"]]
            ),
            "log": st.get("guildLog", [])[:6],
        },
        "worldBoss": st["worldBoss"],
    }


def _quests_payload(st: Dict[str, Any]) -> List[Dict[str, Any]]:
    wk = quests.week_key()
    claimed = set(st.get("claimedQuests", {}).get(wk, []))
    qs = quests.quest_progress(
        quests.weekly_quests(st["class"]), st["history"], st["class"]
    )
    return [{**q, "claimed": q["id"] in claimed} for q in qs]


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


class StartBody(BaseModel):
    mode: str = "demo"  # "demo" | "garmin"


@app.post("/api/onboarding/analyze")
def onboarding_analyze(body: StartBody) -> Dict[str, Any]:
    """S3 'scan': read 4 weeks of history, return the class reveal."""
    try:
        history = _provider_history(body.mode)
    except Exception as exc:  # garmin auth/network failure → actionable error
        raise HTTPException(status_code=502, detail=f"garmin_error: {exc}")
    reco = engine.recommend_class(history)
    return {
        "mode": body.mode,
        "activityCount": len(history),
        "recommendation": reco,
        "classes": {
            k: {kk: vv for kk, vv in v.items() if kk != "activity_types"}
            for k, v in engine.CLASSES.items()
        },
    }


class ChooseBody(BaseModel):
    mode: str = "demo"
    playerClass: str
    playerName: str = "Héros"


@app.post("/api/onboarding/choose")
def onboarding_choose(body: ChooseBody) -> Dict[str, Any]:
    if body.playerClass not in engine.CLASSES:
        raise HTTPException(status_code=400, detail="unknown_class")
    history = _provider_history(body.mode)
    streak = store.streak_from_history(history)
    wellness = _provider_wellness(body.mode)

    # Backfill: your past counts. Grant XP for the analysed history so the
    # player starts with momentum (Duolingo-style head start).
    total_xp = 0
    seen_types: set = set()
    for act in reversed(history):  # oldest first for novelty detection
        novelty = act["activityType"] not in seen_types
        seen_types.add(act["activityType"])
        bd = engine.xp_for_activity(
            act["trainingLoad"], body.playerClass, act["activityType"],
            streak_days=0, readiness=None, new_pr=act.get("isPR", False),
            is_new_activity_type=novelty,
        )
        act["xpBreakdown"] = bd.as_dict()
        total_xp += bd.xp

    level = engine.level_from_total_xp(total_xp)
    boss = engine.spawn_boss(level["level"], _avg_weekly_load(history))
    st = {
        "mode": body.mode,
        "playerName": body.playerName.strip() or "Héros",
        "class": body.playerClass,
        "totalXp": total_xp,
        "streakDays": streak,
        "history": history,
        "seenTypes": sorted(seen_types),
        "boss": boss.as_dict(),
        "lastSyncDate": None,
    }
    _ensure_phase2(st)
    store.save(st)
    return _full_state_payload(st)


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    return _full_state_payload(_require_state())


@app.get("/api/activities")
def get_activities() -> Dict[str, Any]:
    st = _require_state()
    return {"activities": st["history"][:40]}


@app.post("/api/reset")
def reset_profile() -> Dict[str, str]:
    store.reset()
    return {"status": "reset"}


# ---------------------------------------------------------------------------
# Sync — the daily loop
# ---------------------------------------------------------------------------


@app.post("/api/sync")
def sync() -> Dict[str, Any]:
    """Pull (or simulate) the newest session, award XP, damage the boss."""
    st = _require_state()
    wellness = _provider_wellness(st["mode"])

    if st["mode"] == "garmin":
        history = _provider_history("garmin")
        known = {a["activityId"] for a in st["history"]}
        fresh = [a for a in history if a["activityId"] not in known]
        if not fresh:
            return {"newActivities": [], "state": _full_state_payload(st)}
        new_acts = fresh
    else:
        new_acts = [demo_data.simulate_new_activity()]

    level_before = engine.level_from_total_xp(st["totalXp"])["level"]
    metrics = demo_data.demo_metrics(st["history"], wellness, st["streakDays"])
    vitalite = engine.character_sheet(metrics)["vitalite"]
    quests_done_before = {q["id"] for q in _quests_payload(st) if q["done"]}
    div_bonus = quests.diversity_bonus(
        [st["class"]] + [m["class"] for m in st["guild"]["members"]]
    )

    events: List[Dict[str, Any]] = []
    for act in new_acts:
        novelty = act["activityType"] not in set(st.get("seenTypes", []))
        bd = engine.xp_for_activity(
            act["trainingLoad"], st["class"], act["activityType"],
            streak_days=st["streakDays"], readiness=wellness["readiness"],
            new_pr=act.get("isPR", False), is_new_activity_type=novelty,
        )
        act["xpBreakdown"] = bd.as_dict()
        st["totalXp"] += bd.xp
        st["seenTypes"] = sorted(set(st.get("seenTypes", [])) | {act["activityType"]})
        st["history"].insert(0, act)

        boss = engine.Boss(**{
            "name": st["boss"]["name"], "level": st["boss"]["level"],
            "max_hp": st["boss"]["maxHp"], "hp": st["boss"]["hp"],
            "reward_xp": st["boss"]["rewardXp"], "lore": st["boss"]["lore"],
        })
        # Critical hit: an activity matching your class strikes ×1.2
        crit = engine.matches_class(st["class"], act["activityType"])
        eff_load = act["trainingLoad"] * (1.2 if crit else 1.0)
        dmg = engine.damage_boss(boss, eff_load, vitalite)
        boss_defeated = boss.hp <= 0
        if boss_defeated:
            st["totalXp"] += boss.reward_xp
            new_level = engine.level_from_total_xp(st["totalXp"])["level"]
            next_boss = engine.spawn_boss(
                new_level, _avg_weekly_load(st["history"][:30])
            )
            st["boss"] = next_boss.as_dict()
        else:
            st["boss"] = boss.as_dict()

        # World boss: the whole party's damage counts, yours included
        wb = st["worldBoss"]
        wb_dmg = round(eff_load * (0.75 + vitalite / 100 * 0.5) * div_bonus)
        wb["hp"] = max(0, wb["hp"] - wb_dmg)
        wb_defeated = wb["hp"] <= 0
        if wb_defeated:
            st["totalXp"] += wb["rewardXp"]
            st["worldBoss"] = quests.spawn_world_boss(
                _avg_weekly_load(st["history"][:30]), tier=wb["tier"] + 1
            )

        events.append({
            "activity": act,
            "critical": crit,
            "bossDamage": dmg,
            "bossDefeated": boss_defeated,
            "bossRewardXp": boss.reward_xp if boss_defeated else 0,
            "worldBossDamage": wb_dmg,
            "worldBossDefeated": wb_defeated,
            "worldBossRewardXp": wb["rewardXp"] if wb_defeated else 0,
        })

    # Weekly quests: award newly completed ones
    wk = quests.week_key()
    claimed = set(st["claimedQuests"].get(wk, []))
    quest_rewards: List[Dict[str, Any]] = []
    for q in _quests_payload(st):
        if q["done"] and q["id"] not in quests_done_before and q["id"] not in claimed:
            st["totalXp"] += q["rewardXp"]
            claimed.add(q["id"])
            quest_rewards.append({"label": q["label"], "rewardXp": q["rewardXp"]})
    st["claimedQuests"][wk] = sorted(claimed)

    # streak upkeep
    from datetime import date, timedelta
    today = date.today().isoformat()
    if st.get("lastSyncDate") != today:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if st.get("lastSyncDate") == yesterday or st["streakDays"] == 0:
            st["streakDays"] += 1
        st["lastSyncDate"] = today

    level_after_info = engine.level_from_total_xp(st["totalXp"])
    store.save(st)
    return {
        "newActivities": events,
        "questRewards": quest_rewards,
        "levelBefore": level_before,
        "levelAfter": level_after_info["level"],
        "leveledUp": level_after_info["level"] > level_before,
        "state": _full_state_payload(st),
    }


# ---------------------------------------------------------------------------
# Serve the built webapp (single-command "operational app")
# ---------------------------------------------------------------------------

_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="webapp")

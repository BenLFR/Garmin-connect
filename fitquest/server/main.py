"""FitQuest API — FastAPI backend serving the game loop + the built webapp.

Run:  uvicorn main:app --port 8000   (from fitquest/server)
Demo mode needs no Garmin account; mode=garmin uses saved Garth tokens.

Game rules are the v2 science-based engine (see docs/AUDIT_SCIENTIFIQUE.md):
process XP, weekly streaks, recovery XP on rest days, SWC-driven readiness,
anti-spike damage cap on bosses.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from game import cosmetics, demo_data, engine, quests, state as store

app = FastAPI(title="FitQuest API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


def _provider_history(mode: str) -> List[Dict[str, Any]]:
    if mode == "garmin":
        from game.garmin_provider import GarminProvider

        return GarminProvider().history()
    return demo_data.generate_history()


def _provider_wellness(mode: str) -> Dict[str, Any]:
    """Wellness snapshot + SWC vitality status + derived readiness."""
    if mode == "garmin":
        from game.garmin_provider import GarminProvider

        provider = GarminProvider()
        wellness = provider.wellness()
        try:
            series = provider.lnrmssd_series()
        except Exception:
            series = []
        swc = engine.vitality_swc(series)
        wellness["swc"] = swc
        # With enough real HRV history, readiness is SWC-driven like in demo
        # mode; otherwise keep the device readiness already in `wellness`.
        if swc["trend"] is not None:
            wellness["readiness"] = round(
                engine.readiness_from_swc(swc["status"], wellness["sleepScore"])
            )
        return wellness
    wellness = demo_data.demo_wellness()
    swc = engine.vitality_swc(demo_data.lnrmssd_series())
    wellness["swc"] = swc
    wellness["readiness"] = round(
        engine.readiness_from_swc(swc["status"], wellness["sleepScore"])
    )
    return wellness


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def _require_state() -> Dict[str, Any]:
    st = store.load()
    if st is None:
        raise HTTPException(status_code=409, detail="onboarding_required")
    if _ensure_phase2(st):
        store.save(st)
    return st


def _ensure_phase2(st: Dict[str, Any]) -> bool:
    """Lazy-init guild/world-boss/quest fields + apply NPC daily ticks."""
    changed = False
    if "guild" not in st:
        st["guild"] = quests.spawn_guild(st["class"])
        changed = True
    if "worldBoss" not in st:
        st["worldBoss"] = quests.spawn_world_boss(_avg_weekly_load(st["history"]))
        changed = True
    st.setdefault("claimedQuests", {})
    st.setdefault("guildLog", [])
    st.setdefault("restRewards", [])
    st.setdefault("bossKills", 0)
    st.setdefault("equipped", {slot: None for slot in cosmetics.SLOTS})

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


def _week_streak(history: List[Dict[str, Any]]) -> int:
    return engine.successful_week_streak(store.active_days_by_week(history))


def _current_week_acts(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    monday = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    return [a for a in history if a.get("startDate", "") >= monday]


def _spike_guard(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Player-facing view of the anti-spike rule: the cap and the biggest
    session it derives from (cap = 110 % of that session's load)."""
    cap = engine.anti_spike_cap(history)
    return {
        "cap": cap,
        "biggestSession": round(cap / 1.10, 1) if cap is not None else None,
    }


def _full_state_payload(st: Dict[str, Any]) -> Dict[str, Any]:
    wellness = _provider_wellness(st["mode"])
    week_streak = _week_streak(st["history"])
    metrics = demo_data.demo_metrics(st["history"], wellness, week_streak)
    sheet = engine.character_sheet(metrics)
    level = engine.level_from_total_xp(st["totalXp"])
    cls = engine.CLASSES[st["class"]]
    active_days = store.active_days_this_week(st["history"])
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
        "weekStreak": week_streak,
        "weekPattern": {
            "activeDaysThisWeek": active_days,
            "healthyMin": engine.HEALTHY_WEEK_MIN_DAYS,
            "healthyMax": engine.HEALTHY_WEEK_MAX_DAYS,
        },
        "intensity": engine.intensity_budget(_current_week_acts(st["history"])),
        "spikeGuard": _spike_guard(st["history"]),
        "wellness": wellness,
        "characterSheet": sheet,
        "boss": st["boss"],
        "cosmetics": cosmetics.payload(st, level["level"]),
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
# Garmin auth — in-app SSO login with two-step MFA
# ---------------------------------------------------------------------------


class GarminLoginBody(BaseModel):
    email: str
    password: str  # single use: forwarded to SSO, never logged or stored


class GarminMfaBody(BaseModel):
    code: str


_AUTH_HTTP_CODES = {
    "bad_credentials": 401,
    "bad_mfa_code": 401,
    "rate_limited": 429,
    "no_pending_login": 409,
    "garmin_error": 502,
}


def _auth_http_error(exc: "garmin_auth.AuthError") -> HTTPException:
    return HTTPException(status_code=_AUTH_HTTP_CODES.get(exc.code, 502),
                         detail=exc.code)


@app.get("/api/garmin/status")
def garmin_status() -> Dict[str, Any]:
    from game import garmin_auth

    return garmin_auth.token_status()


@app.post("/api/garmin/login")
def garmin_login(body: GarminLoginBody) -> Dict[str, str]:
    from game import garmin_auth

    try:
        return garmin_auth.start_login(body.email, body.password)
    except garmin_auth.AuthError as exc:
        raise _auth_http_error(exc)


@app.post("/api/garmin/mfa")
def garmin_mfa(body: GarminMfaBody) -> Dict[str, str]:
    from game import garmin_auth

    try:
        return garmin_auth.submit_mfa(body.code)
    except garmin_auth.AuthError as exc:
        raise _auth_http_error(exc)


# ---------------------------------------------------------------------------
# Onboarding
# ---------------------------------------------------------------------------


class StartBody(BaseModel):
    mode: str = "demo"  # "demo" | "garmin"


@app.post("/api/onboarding/analyze")
def onboarding_analyze(body: StartBody) -> Dict[str, Any]:
    try:
        history = _provider_history(body.mode)
    except Exception as exc:
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

    # Backfill: your past counts — process XP over the analysed history,
    # replaying each week so the intensity-distribution guardrail applies.
    total_xp = 0
    seen_types: set = set()
    week_acts: List[Dict[str, Any]] = []
    current_week = None
    for act in reversed(history):  # oldest first
        act_week = quests.week_key(date.fromisoformat(act["startDate"]))
        if act_week != current_week:
            current_week, week_acts = act_week, []
        novelty = act["activityType"] not in seen_types
        seen_types.add(act["activityType"])
        bd = engine.xp_for_activity(
            act, body.playerClass, week_activities=week_acts,
            successful_weeks=0, readiness=None, is_new_activity_type=novelty,
        )
        act["xpBreakdown"] = bd.as_dict()
        total_xp += bd.xp
        week_acts.append(act)

    level = engine.level_from_total_xp(total_xp)
    boss = engine.spawn_boss(level["level"], _avg_weekly_load(history))
    st = {
        "mode": body.mode,
        "playerName": body.playerName.strip() or "Héros",
        "class": body.playerClass,
        "totalXp": total_xp,
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
    """Pull (or simulate) the newest session, award process XP, damage the
    bosses (anti-spike capped), reward compliant rest days and quests."""
    st = _require_state()
    wellness = _provider_wellness(st["mode"])
    readiness = wellness.get("readiness")

    if st["mode"] == "garmin":
        history = _provider_history("garmin")
        known = {a["activityId"] for a in st["history"]}
        fresh = [a for a in history if a["activityId"] not in known]
        if not fresh:
            return {"newActivities": [], "questRewards": [],
                    "recoveryReward": None, "state": _full_state_payload(st)}
        new_acts = fresh
    else:
        new_acts = [demo_data.simulate_new_activity()]

    level_before = engine.level_from_total_xp(st["totalXp"])["level"]
    week_streak = _week_streak(st["history"])
    metrics = demo_data.demo_metrics(st["history"], wellness, week_streak)
    vitalite = engine.character_sheet(metrics)["vitalite"]
    quests_done_before = {q["id"] for q in _quests_payload(st) if q["done"]}
    div_bonus = quests.diversity_bonus(
        [st["class"]] + [m["class"] for m in st["guild"]["members"]]
    )

    level_before_info = engine.level_from_total_xp(st["totalXp"])
    unlocked_before = set(cosmetics.unlocked_ids(
        cosmetics.player_counters(st, level_before_info["level"])
    ))

    # Recovery XP: yesterday was a genuine rest day in an active week →
    # rest is a rewarded play action (once per day).
    recovery_reward = None
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    active_dates = {a.get("startDate") for a in st["history"]}
    if (yesterday not in active_dates
            and yesterday not in st["restRewards"]
            and store.active_days_this_week(st["history"]) >= 1):
        xp_rest = engine.recovery_xp_for_rest_day(
            store.active_days_this_week(st["history"])
        )
        if xp_rest > 0:
            st["totalXp"] += xp_rest
            st["restRewards"] = (st["restRewards"] + [yesterday])[-30:]
            recovery_reward = {"date": yesterday, "xp": xp_rest}

    events: List[Dict[str, Any]] = []
    for act in new_acts:
        spike_cap = engine.anti_spike_cap(st["history"])
        novelty = act["activityType"] not in set(st.get("seenTypes", []))
        bd = engine.xp_for_activity(
            act, st["class"],
            week_activities=_current_week_acts(st["history"]),
            successful_weeks=week_streak, readiness=readiness,
            is_new_activity_type=novelty,
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
        crit = engine.matches_class(st["class"], act["activityType"])
        hit = engine.damage_boss(
            boss, act["trainingLoad"] * (1.2 if crit else 1.0),
            vitalite, spike_cap=spike_cap,
        )
        boss_defeated = boss.hp <= 0
        if boss_defeated:
            st["totalXp"] += boss.reward_xp
            st["bossKills"] = st.get("bossKills", 0) + 1
            new_level = engine.level_from_total_xp(st["totalXp"])["level"]
            st["boss"] = engine.spawn_boss(
                new_level, _avg_weekly_load(st["history"][:30])
            ).as_dict()
        else:
            st["boss"] = boss.as_dict()

        # World boss: same capped, vitality-scaled damage + guild bonus
        effective = min(act["trainingLoad"], spike_cap) if spike_cap else act["trainingLoad"]
        if crit:
            effective *= 1.2
        wb = st["worldBoss"]
        wb_dmg = round(effective * (0.75 + vitalite / 100 * 0.5) * div_bonus)
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
            "spikeCapped": hit["capped"],
            "bossDamage": hit["damage"],
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

    st["lastSyncDate"] = date.today().isoformat()
    level_after_info = engine.level_from_total_xp(st["totalXp"])
    new_cosmetics = [
        {"id": item["id"], "slot": item["slot"], "name": item["name"]}
        for item in cosmetics.ITEMS
        if item["id"] not in unlocked_before and cosmetics.is_unlocked(
            item, cosmetics.player_counters(st, level_after_info["level"])
        )
    ]
    store.save(st)
    return {
        "newActivities": events,
        "questRewards": quest_rewards,
        "recoveryReward": recovery_reward,
        "newCosmetics": new_cosmetics,
        "levelBefore": level_before,
        "levelAfter": level_after_info["level"],
        "leveledUp": level_after_info["level"] > level_before,
        "state": _full_state_payload(st),
    }


# ---------------------------------------------------------------------------
# Cosmetics — equip/unequip unlocked items
# ---------------------------------------------------------------------------


class EquipBody(BaseModel):
    slot: str
    itemId: Optional[str] = None  # None = unequip


@app.post("/api/cosmetics/equip")
def equip_cosmetic(body: EquipBody) -> Dict[str, Any]:
    st = _require_state()
    if body.slot not in cosmetics.SLOTS:
        raise HTTPException(status_code=400, detail="unknown_slot")
    if body.itemId is not None:
        item = cosmetics.get_item(body.itemId)
        if item is None:
            raise HTTPException(status_code=400, detail="unknown_item")
        if item["slot"] != body.slot:
            raise HTTPException(status_code=400, detail="wrong_slot")
        level = engine.level_from_total_xp(st["totalXp"])["level"]
        if not cosmetics.is_unlocked(item, cosmetics.player_counters(st, level)):
            raise HTTPException(status_code=403, detail="item_locked")
    st.setdefault("equipped", {slot: None for slot in cosmetics.SLOTS})
    st["equipped"][body.slot] = body.itemId
    store.save(st)
    return _full_state_payload(st)


# ---------------------------------------------------------------------------
# Serve the built webapp (single-command "operational app")
# ---------------------------------------------------------------------------

_DIST = Path(__file__).resolve().parent.parent / "webapp" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="webapp")

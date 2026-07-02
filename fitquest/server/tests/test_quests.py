"""Phase 2 rules — weekly quests, guild diversity, world boss."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import quests  # noqa: E402


def _monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


# -- weekly quests ------------------------------------------------------------

def test_weekly_quests_are_three_and_deterministic():
    a = quests.weekly_quests("rodeur")
    b = quests.weekly_quests("rodeur")
    assert len(a) == 3 and a == b  # same week → same quests
    assert a[-1]["id"] == "c_rodeur"  # one is always class-flavored


def test_quests_rotate_between_weeks():
    d1 = date(2026, 6, 1)
    d2 = date(2026, 6, 8)
    assert quests.week_key(d1) != quests.week_key(d2)
    ids = lambda d: [q["id"] for q in quests.weekly_quests("rodeur", d)]
    # rotation over several weeks must produce at least one differing set
    assert any(ids(d1) != ids(d1 + timedelta(weeks=k)) for k in range(1, 5))


def test_quest_progress_counts_only_current_week():
    monday = _monday()
    history = [
        {"activityType": "running", "activityName": "x", "startDate": monday.isoformat(),
         "durationMinutes": 70, "trainingLoad": 100, "isPR": True},
        {"activityType": "running", "activityName": "old", "startDate": "2020-01-01",
         "durationMinutes": 500, "trainingLoad": 999, "isPR": True},
    ]
    qs = quests.quest_progress(
        [{"id": "g_sessions3", "label": "", "metric": "sessions", "target": 3, "rewardXp": 1},
         {"id": "g_load400", "label": "", "metric": "load", "target": 400, "rewardXp": 1},
         {"id": "c_rodeur", "label": "", "metric": "class_minutes", "target": 120, "rewardXp": 1}],
        history, "rodeur",
    )
    by_id = {q["id"]: q for q in qs}
    assert by_id["g_sessions3"]["progress"] == 1  # the 2020 activity is ignored
    assert by_id["g_load400"]["progress"] == 100
    assert by_id["c_rodeur"]["progress"] == 70


def test_completed_quest_is_flagged_done():
    monday = _monday()
    history = [{"activityType": "running", "activityName": "x",
                "startDate": monday.isoformat(), "durationMinutes": 65,
                "trainingLoad": 10, "isPR": False}]
    qs = quests.quest_progress(
        [{"id": "g_long60", "label": "", "metric": "long_session_min",
          "target": 60, "rewardXp": 1}],
        history, "rodeur",
    )
    assert qs[0]["done"] and qs[0]["progress"] == 60  # progress is capped


# -- guild / diversity ----------------------------------------------------------

def test_diversity_bonus_caps_at_20_percent():
    assert quests.diversity_bonus(["rodeur"]) == 1.0
    assert quests.diversity_bonus(["rodeur", "assassin"]) == 1.05
    assert quests.diversity_bonus(
        ["rodeur", "assassin", "guerrier", "paladin", "voyageur", "rodeur"]
    ) == 1.20


def test_guild_complements_player_class():
    guild = quests.spawn_guild("rodeur")
    assert len(guild["members"]) == 4
    # NPCs are picked to diversify: player's own class comes last in the pool
    assert sum(1 for m in guild["members"] if m["class"] == "rodeur") <= 1


# -- world boss ------------------------------------------------------------------

def test_world_boss_scales_with_party_and_tier():
    b1 = quests.spawn_world_boss(400, tier=1)
    b2 = quests.spawn_world_boss(400, tier=3)
    assert b1["maxHp"] == 2000  # 400 × 5 companions
    assert b2["maxHp"] > b1["maxHp"]
    assert b2["rewardXp"] > b1["rewardXp"]


def test_npc_damage_accumulates_over_missed_days():
    guild = quests.spawn_guild("rodeur")
    none = quests.npc_daily_damage(guild, 0, 400, seed=1)
    week = quests.npc_daily_damage(guild, 7, 400, seed=1)
    assert none == []
    assert len(week) > 5  # 4 NPCs × ~4.5 j/7 ≈ 18 hits
    assert all(h["damage"] > 0 for h in week)

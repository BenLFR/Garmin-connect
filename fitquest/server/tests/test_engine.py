"""Engine v2 rules regression tests.

Each test pins a science-based ruling from docs/AUDIT_SCIENTIFIQUE.md —
if a test fails, either the code or the science doc must be re-examined.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import engine  # noqa: E402


def _act(minutes=60, a_type="running", anaerobic=0.5, load=100.0):
    return {"activityType": a_type, "durationMinutes": minutes,
            "anaerobicTE": anaerobic, "trainingLoad": load}


# -- Process XP (audit: process goals d=1.36 vs outcome d=0.09) ----------------

def test_xp_is_per_minute_not_per_load():
    """A slow Z1 hour and a hard Z3 hour pay the same: intensity is not
    the currency, time on feet is."""
    easy = engine.xp_for_activity(_act(60, anaerobic=0.2, load=50), "rodeur")
    hard = engine.xp_for_activity(_act(60, anaerobic=1.8, load=200), "rodeur")
    assert easy.xp == hard.xp == 180  # 60 min × 2 × 1.5 classe


def test_class_match_multiplies_xp():
    on = engine.xp_for_activity(_act(a_type="running"), "rodeur")
    off = engine.xp_for_activity(_act(a_type="strength_training"), "rodeur")
    assert on.xp == 180 and off.xp == 120


def test_pr_earns_no_xp_anymore():
    """PRs push unplanned max efforts — trophy only, no XP field exists."""
    bd = engine.xp_for_activity(_act(), "rodeur")
    assert "prBonus" not in bd.as_dict()


def test_red_readiness_still_caps_xp():
    red = engine.xp_for_activity(_act(), "rodeur", readiness=10)
    green = engine.xp_for_activity(_act(), "rodeur", readiness=80)
    assert red.xp == 54 and green.xp == 180  # ×0.3 vs ×1.0
    assert engine.readiness_cap(30) == 0.7


# -- Intensity distribution guardrail (HIIT ≈ 20 % of volume) -------------------

def test_intense_work_beyond_20pct_budget_is_discounted():
    week = [_act(240, anaerobic=0.3)]  # 240 easy minutes already done
    within = engine.xp_for_activity(
        _act(50, a_type="hiit", anaerobic=3.0), "assassin",
        week_activities=week)
    # 50/290 ≈ 17 % intense → full price
    assert within.tid_factor == 1.0
    over = engine.xp_for_activity(
        _act(90, a_type="hiit", anaerobic=3.0), "assassin",
        week_activities=week)
    # 90/330 ≈ 27 % intense → discounted
    assert over.tid_factor == engine.TID_DISCOUNT


def test_easy_sessions_are_never_discounted():
    week = [_act(30, a_type="hiit", anaerobic=3.0)]
    bd = engine.xp_for_activity(_act(30, anaerobic=0.2), "rodeur",
                                week_activities=week)
    assert bd.tid_factor == 1.0


# -- Weekly streak (audit: daily streaks trigger AVE + tissue overload) ---------

def test_successful_week_is_3_to_5_active_days():
    assert not engine.is_successful_week(2)   # not enough stimulus
    assert engine.is_successful_week(3)
    assert engine.is_successful_week(5)
    assert not engine.is_successful_week(7)   # no rest = not successful


def test_week_streak_multiplier_caps_at_4_weeks():
    assert engine.week_streak_multiplier(0) == 1.0
    assert engine.week_streak_multiplier(4) == engine.week_streak_multiplier(9) == 1.2


def test_week_streak_counts_consecutive_successful_weeks():
    assert engine.successful_week_streak([4, 3, 5, 7, 4]) == 3
    assert engine.successful_week_streak([7, 4, 4]) == 0


def test_rest_day_earns_recovery_xp_in_active_week():
    assert engine.recovery_xp_for_rest_day(3) == engine.RECOVERY_XP
    assert engine.recovery_xp_for_rest_day(0) == 0  # full couch ≠ recovery


# -- Vitality SWC (Plews & Buchheit; Manresa-Rocamora 2021) ---------------------

def test_swc_flags_parasympathetic_suppression():
    baseline = [4.2] * 53
    crashed = baseline + [3.4] * 7  # 7-day trend far below baseline - SWC
    assert engine.vitality_swc(crashed)["status"] == "debuff"


def test_swc_flags_supercompensation_and_normal():
    stable = [4.2, 4.25, 4.15, 4.3, 4.1] * 12
    assert engine.vitality_swc(stable)["status"] == "normal"
    surging = stable + [4.9] * 7
    assert engine.vitality_swc(surging[-60:])["status"] == "buff"


def test_swc_needs_enough_data():
    assert engine.vitality_swc([4.2] * 5)["status"] == "normal"


def test_readiness_from_swc_penalises_short_sleep():
    fresh = engine.readiness_from_swc("buff", sleep_score=90)
    tired = engine.readiness_from_swc("debuff", sleep_score=40)
    assert fresh == 85.0 and tired == 20.0  # 35 - 15 sommeil court


# -- Boss & anti-spike cap (Frandsen BJSM 2025: spikes = +52-64 % injuries) -----

def test_boss_hp_is_one_typical_week_no_stretch():
    boss = engine.spawn_boss(player_level=3, avg_weekly_load=400)
    assert boss.max_hp == 400  # ×1.0, plus de ×1.15


def test_single_session_damage_is_spike_capped():
    today = date.today().isoformat()
    history = [{"trainingLoad": 100, "startDate": today}]
    cap = engine.anti_spike_cap(history)
    assert cap == 110.0  # 110 % du pic des 30 derniers jours

    boss = engine.spawn_boss(1, 1000)
    hit = engine.damage_boss(boss, 500, vitalite=50, spike_cap=cap)
    assert hit["capped"] is True
    assert hit["damage"] == 110  # 110 × (0.75 + 0.25) : l'héroïsme ne paie pas


def test_old_sessions_do_not_feed_the_spike_cap():
    old = (date.today() - timedelta(days=45)).isoformat()
    assert engine.anti_spike_cap([{"trainingLoad": 300, "startDate": old}]) is None


def test_vitalite_scales_boss_damage():
    b1, b2 = engine.spawn_boss(1, 400), engine.spawn_boss(1, 400)
    tired = engine.damage_boss(b1, 100, vitalite=0)["damage"]
    fresh = engine.damage_boss(b2, 100, vitalite=100)["damage"]
    assert (tired, fresh) == (75, 125)


def test_boss_hp_never_negative():
    boss = engine.spawn_boss(1, 400)
    engine.damage_boss(boss, 10_000, vitalite=100)
    assert boss.hp == 0 and boss.as_dict()["defeated"]


# -- Level curve (unchanged) -----------------------------------------------------

def test_level_curve_unchanged():
    assert engine.xp_to_next(1) == 100
    assert engine.level_from_total_xp(1_703)["level"] == 5
    assert engine.level_from_total_xp(11_106)["level"] == 10


# -- Recommendation (unchanged) ---------------------------------------------------

def test_recommendation_is_load_weighted():
    acts = [
        {"activityType": "running", "trainingLoad": 300, "elevationGain": 0},
        {"activityType": "strength_training", "trainingLoad": 40,
         "elevationGain": 0},
    ]
    assert engine.recommend_class(acts)["recommended"] == "rodeur"


def test_blank_history_defaults_to_voyageur():
    assert engine.recommend_class([])["recommended"] == "voyageur"


# -- Character sheet ---------------------------------------------------------------

def test_character_sheet_is_bounded_and_complete():
    sheet = engine.character_sheet({
        "enduranceScore": 20_000, "weeklyAerobicMinutes": 10_000,
        "vo2max": 90, "maxPower": 2_000, "strengthLoad4w": 5_000,
        "anaerobicTE": 9, "hrvStatusScore": 100, "sleepScore": 100,
        "readiness": 100, "weekStreak": 9, "activeDaysPerWeek": 7,
    })
    assert set(sheet) == {"stamina", "force", "agilite", "vitalite",
                          "discipline"}
    assert all(0 <= v <= 100 for v in sheet.values())

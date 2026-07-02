"""Engine rules regression tests — each test pins a GAME_DESIGN.md rule."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import engine  # noqa: E402


# -- XP formula -------------------------------------------------------------

def test_class_match_multiplies_xp():
    on = engine.xp_for_activity(100, "rodeur", "running")
    off = engine.xp_for_activity(100, "rodeur", "strength_training")
    assert on.xp == 150 and off.xp == 100


def test_streak_caps_at_seven_days():
    assert engine.streak_multiplier(7) == engine.streak_multiplier(30) == 1.35
    assert engine.streak_multiplier(0) == 1.0


def test_red_readiness_nearly_cuts_xp():
    red = engine.xp_for_activity(100, "rodeur", "running", readiness=10)
    green = engine.xp_for_activity(100, "rodeur", "running", readiness=80)
    assert red.xp == 45  # 100 × 1.5 × 0.3
    assert green.xp == 150
    assert engine.readiness_cap(30) == 0.7


def test_pr_bonus_is_flat_and_uncapped_by_readiness():
    bd = engine.xp_for_activity(100, "rodeur", "running",
                                readiness=10, new_pr=True)
    assert bd.xp == 45 + 200  # the PR bonus is never punished


def test_voyageur_rewards_novelty_not_type():
    new = engine.xp_for_activity(100, "voyageur", "curling",
                                 is_new_activity_type=True)
    seen = engine.xp_for_activity(100, "voyageur", "curling",
                                  is_new_activity_type=False)
    assert new.xp == 150 and seen.xp == 100


def test_negative_load_never_yields_xp():
    assert engine.xp_for_activity(-50, "rodeur", "running").xp == 0


# -- Level curve --------------------------------------------------------------

def test_level_curve_matches_design_doc():
    assert engine.xp_to_next(1) == 100
    assert engine.level_from_total_xp(0)["level"] == 1
    assert engine.level_from_total_xp(100)["level"] == 2
    assert engine.level_from_total_xp(1_703)["level"] == 5
    assert engine.level_from_total_xp(11_106)["level"] == 10


def test_level_progress_fields_are_consistent():
    info = engine.level_from_total_xp(250)
    assert info["level"] == 2
    assert info["xpInLevel"] == 150
    assert info["xpToNext"] == engine.xp_to_next(2)


# -- Recommendation -----------------------------------------------------------

def test_recommendation_is_load_weighted():
    acts = [
        {"activityType": "running", "trainingLoad": 300, "elevationGain": 0},
        {"activityType": "strength_training", "trainingLoad": 40,
         "elevationGain": 0},
    ]
    reco = engine.recommend_class(acts)
    assert reco["recommended"] == "rodeur"
    assert sum(reco["affinities"].values()) > 0


def test_blank_history_defaults_to_voyageur():
    assert engine.recommend_class([])["recommended"] == "voyageur"


def test_big_ascent_feeds_paladin():
    acts = [{"activityType": "cycling", "trainingLoad": 10,
             "elevationGain": 1500}]
    reco = engine.recommend_class(acts)
    assert reco["affinities"]["paladin"] > 0


# -- Character sheet ----------------------------------------------------------

def test_character_sheet_is_bounded_and_complete():
    sheet = engine.character_sheet({
        "enduranceScore": 20_000, "weeklyAerobicMinutes": 10_000,
        "vo2max": 90, "maxPower": 2_000, "strengthLoad4w": 5_000,
        "anaerobicTE": 9, "hrvStatusScore": 100, "sleepScore": 100,
        "readiness": 100, "streakDays": 99, "activeDaysPerWeek": 7,
    })
    assert set(sheet) == {"stamina", "force", "agilite", "vitalite",
                          "discipline"}
    assert all(0 <= v <= 100 for v in sheet.values())
    assert engine.character_sheet({})["vitalite"] == 0


# -- Boss ----------------------------------------------------------------------

def test_boss_is_calibrated_on_weekly_load():
    boss = engine.spawn_boss(player_level=3, avg_weekly_load=400)
    assert boss.max_hp == 460  # 400 × 1.15 : un stretch, pas un mur
    assert boss.hp == boss.max_hp


def test_vitalite_scales_boss_damage():
    b1 = engine.spawn_boss(1, 400)
    b2 = engine.spawn_boss(1, 400)
    dmg_tired = engine.damage_boss(b1, 100, vitalite=0)
    dmg_fresh = engine.damage_boss(b2, 100, vitalite=100)
    assert dmg_tired == 75 and dmg_fresh == 125  # le repos rend plus fort


def test_boss_hp_never_negative():
    boss = engine.spawn_boss(1, 400)
    engine.damage_boss(boss, 10_000, vitalite=100)
    assert boss.hp == 0 and boss.as_dict()["defeated"]

"""Cosmetic loot rules — the SCIENCE.md no-volume-reward guardrail."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import cosmetics  # noqa: E402


def _counters(level=1, boss_kills=0, wb_tier=1, quests_claimed=0):
    return {"level": level, "bossKills": boss_kills,
            "worldBossTier": wb_tier, "questsClaimed": quests_claimed}


def test_no_item_unlocks_on_volume():
    """SCIENCE.md guardrail: rewards indexed on raw load/volume re-create
    the grinding incentive. Only process/consistency counters allowed."""
    for item in cosmetics.ITEMS:
        assert item["unlock"]["type"] in cosmetics.VALID_UNLOCKS, item["id"]


def test_item_ids_unique_and_slots_valid():
    ids = [item["id"] for item in cosmetics.ITEMS]
    assert len(ids) == len(set(ids))
    assert all(item["slot"] in cosmetics.SLOTS for item in cosmetics.ITEMS)


def test_unlock_thresholds():
    ids = set(cosmetics.unlocked_ids(_counters(level=5)))
    assert {"t_novice", "t_eveille", "g_bandeau"} <= ids
    assert "g_epee" not in ids       # needs a boss kill
    assert "t_vaillant" not in ids   # needs level 10


def test_boss_kill_unlocks_exclusive():
    assert "g_epee" in cosmetics.unlocked_ids(_counters(boss_kills=1))
    assert "g_bouclier" not in cosmetics.unlocked_ids(_counters(boss_kills=1))
    assert "g_bouclier" in cosmetics.unlocked_ids(_counters(boss_kills=3))


def test_world_boss_tier_unlocks_wings():
    assert "g_aile" not in cosmetics.unlocked_ids(_counters(wb_tier=1))
    assert "g_aile" in cosmetics.unlocked_ids(_counters(wb_tier=2))


def test_player_counters_reads_state():
    st = {"bossKills": 2, "worldBoss": {"tier": 3},
          "claimedQuests": {"2026-W26": ["a", "b"], "2026-W27": ["c"]}}
    counters = cosmetics.player_counters(st, level=7)
    assert counters == {"level": 7, "bossKills": 2,
                        "worldBossTier": 3, "questsClaimed": 3}


def test_payload_marks_unlocked_and_labels():
    st = {"bossKills": 1, "worldBoss": {"tier": 1}, "claimedQuests": {},
          "equipped": {"title": None, "halo": None, "gear": "g_epee"}}
    payload = cosmetics.payload(st, level=4)
    by_id = {item["id"]: item for item in payload["items"]}
    assert by_id["g_epee"]["unlocked"] is True
    assert by_id["t_vaillant"]["unlocked"] is False
    assert by_id["t_vaillant"]["unlockLabel"] == "Niveau 10"
    assert payload["equipped"]["gear"] == "g_epee"


def test_equip_endpoint_refuses_locked_item(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import main
    from game import state as store

    monkeypatch.setattr(store, "STATE_FILE", tmp_path / "state.json")
    st = {
        "mode": "demo", "playerName": "T", "class": "rodeur", "totalXp": 0,
        "history": [], "seenTypes": [], "lastSyncDate": None,
        "boss": {"name": "b", "level": 1, "maxHp": 10, "hp": 10,
                 "rewardXp": 10, "lore": "", "defeated": False},
    }
    store.save(st)
    client = TestClient(main.app)

    resp = client.post("/api/cosmetics/equip",
                       json={"slot": "gear", "itemId": "g_couronne"})
    assert resp.status_code == 403
    assert resp.json() == {"detail": "item_locked"}

    resp = client.post("/api/cosmetics/equip",
                       json={"slot": "gear", "itemId": "t_novice"})
    assert resp.status_code == 400  # wrong_slot

    resp = client.post("/api/cosmetics/equip",
                       json={"slot": "hat", "itemId": None})
    assert resp.status_code == 400  # unknown_slot

    # level 1 unlocks nothing, but unequipping is always allowed
    resp = client.post("/api/cosmetics/equip",
                       json={"slot": "gear", "itemId": None})
    assert resp.status_code == 200
    assert resp.json()["cosmetics"]["equipped"]["gear"] is None

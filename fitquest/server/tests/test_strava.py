"""Strava provider — contract mapping, load proxies, OAuth plumbing."""

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import strava_auth, strava_provider  # noqa: E402


def _summary(**over):
    base = {
        "id": 987, "name": "Morning Run", "sport_type": "Run",
        "start_date_local": "2026-07-01T08:00:00Z",
        "moving_time": 3600, "total_elevation_gain": 120.0,
        "average_heartrate": 156.0, "suffer_score": 85.0, "pr_count": 0,
        "start_latlng": [59.24, 18.0],
        "map": {"summary_polyline": "abc"},
    }
    base.update(over)
    return base


# -- activity mapping ---------------------------------------------------------

def test_map_activity_contract_shape():
    act = strava_provider.map_activity(_summary())
    assert act["activityType"] == "running"
    assert act["startDate"] == "2026-07-01"
    assert act["durationMinutes"] == 60
    assert act["trainingLoad"] == 85.0          # Relative Effort wins
    assert act["hasPolyline"] is True
    assert act["startLatitude"] == 59.24
    # every field the engine/demo contract expects is present
    expected = {"activityId", "activityType", "activityName", "startDate",
                "durationMinutes", "trainingLoad", "elevationGain",
                "aerobicTE", "anaerobicTE", "isPR",
                "startLatitude", "startLongitude", "hasPolyline"}
    assert expected <= set(act)


def test_load_falls_back_to_hr_proxy_then_duration():
    with_hr = strava_provider.map_activity(_summary(suffer_score=None))
    assert with_hr["trainingLoad"] == pytest.approx(60 * 156 / 130, rel=0.01)
    bare = strava_provider.map_activity(
        _summary(suffer_score=None, average_heartrate=None))
    assert bare["trainingLoad"] == pytest.approx(48.0)  # minutes × 0.8


def test_sport_types_map_to_engine_vocabulary():
    for sport, expected in [("TrailRun", "trail_running"),
                            ("WeightTraining", "strength_training"),
                            ("HighIntensityIntervalTraining", "hiit"),
                            ("SurfSession", "other")]:
        assert strava_provider.map_activity(
            _summary(sport_type=sport))["activityType"] == expected


def test_intense_types_get_stronger_anaerobic_proxy():
    hiit = strava_provider.map_activity(
        _summary(sport_type="HighIntensityIntervalTraining"))
    run = strava_provider.map_activity(_summary())
    assert hiit["anaerobicTE"] > run["anaerobicTE"]


# -- OAuth plumbing -----------------------------------------------------------

@pytest.fixture()
def _tmp_files(monkeypatch, tmp_path):
    monkeypatch.setattr(strava_auth, "APP_FILE", tmp_path / "app.json")
    monkeypatch.setattr(strava_auth, "TOKEN_FILE", tmp_path / "tok.json")
    monkeypatch.setattr(strava_auth, "DATA_DIR", tmp_path)
    monkeypatch.delenv("STRAVA_CLIENT_ID", raising=False)
    monkeypatch.delenv("STRAVA_CLIENT_SECRET", raising=False)
    return tmp_path


def test_status_unconfigured(_tmp_files):
    assert strava_auth.status() == {"configured": False, "connected": False}


def test_authorize_url_needs_config(_tmp_files):
    with pytest.raises(strava_auth.StravaAuthError):
        strava_auth.authorize_url("http://localhost:8000/cb")


def test_authorize_url_with_env(monkeypatch, _tmp_files):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "123")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "s")
    url = strava_auth.authorize_url("http://localhost:8000/cb")
    assert url.startswith(strava_auth.AUTHORIZE_URL)
    assert "client_id=123" in url and "activity%3Aread_all" in url


def test_access_token_uses_fresh_token_without_network(_tmp_files):
    strava_auth._save_tokens({"access_token": "AT", "refresh_token": "RT",
                              "expires_at": time.time() + 3600})
    assert strava_auth.access_token() == "AT"


def test_access_token_refreshes_expired(monkeypatch, _tmp_files):
    monkeypatch.setenv("STRAVA_CLIENT_ID", "123")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "s")
    strava_auth._save_tokens({"access_token": "OLD", "refresh_token": "RT",
                              "expires_at": time.time() - 10})

    class FakeResp:
        status_code = 200

        def json(self):
            return {"access_token": "NEW", "refresh_token": "RT2",
                    "expires_at": time.time() + 3600}

    import requests

    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResp())
    assert strava_auth.access_token() == "NEW"
    assert strava_auth._load_tokens()["refresh_token"] == "RT2"


# -- API layer ----------------------------------------------------------------

def test_status_endpoint(_tmp_files):
    from fastapi.testclient import TestClient

    import main

    resp = TestClient(main.app).get("/api/strava/status")
    assert resp.status_code == 200
    assert resp.json() == {"configured": False, "connected": False}


def test_connect_endpoint_unconfigured_is_503(_tmp_files):
    from fastapi.testclient import TestClient

    import main

    resp = TestClient(main.app).get("/api/strava/connect",
                                    follow_redirects=False)
    assert resp.status_code == 503
    assert resp.json() == {"detail": "not_configured"}

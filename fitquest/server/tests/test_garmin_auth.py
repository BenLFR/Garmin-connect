"""In-app Garmin login flow — two-step MFA, no credential leakage."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game import garmin_auth  # noqa: E402


class FakeClient:
    def __init__(self):
        self.dumped_to = None
        self.oauth1_token = None
        self.oauth2_token = None

    def dump(self, path, **kwargs):
        self.dumped_to = path


@pytest.fixture(autouse=True)
def _clean_pending():
    garmin_auth._pending.clear()
    yield
    garmin_auth._pending.clear()


def _patch_garth(monkeypatch, login=None, resume=None, client_cls=FakeClient):
    import garth.http
    import garth.sso

    monkeypatch.setattr(garth.http, "Client", client_cls)
    if login is not None:
        monkeypatch.setattr(garth.sso, "login", login)
    if resume is not None:
        monkeypatch.setattr(garth.sso, "resume_login", resume)


def test_start_login_returns_mfa_state(monkeypatch):
    state = {"login_params": {}, "client": FakeClient(), "mfa_method": "email"}
    _patch_garth(monkeypatch, login=lambda *a, **k: ("needs_mfa", state))
    res = garmin_auth.start_login("a@b.c", "secret")
    assert res == {"status": "mfa_required", "mfaMethod": "email"}
    assert garmin_auth._pending["client_state"] is state


def test_start_login_success_dumps_tokens(monkeypatch):
    _patch_garth(monkeypatch, login=lambda *a, **k: ("tok1", "tok2"))
    res = garmin_auth.start_login("a@b.c", "secret")
    assert res == {"status": "connected"}
    assert garmin_auth._pending == {}


def test_start_login_maps_errors(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("Error in request: 429 Client Error")

    _patch_garth(monkeypatch, login=boom)
    with pytest.raises(garmin_auth.AuthError) as exc:
        garmin_auth.start_login("a@b.c", "secret")
    assert exc.value.code == "rate_limited"
    assert "secret" not in str(exc.value)


def test_start_login_bad_credentials(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("401 Client Error: Unauthorized")

    _patch_garth(monkeypatch, login=boom)
    with pytest.raises(garmin_auth.AuthError) as exc:
        garmin_auth.start_login("a@b.c", "secret")
    assert exc.value.code == "bad_credentials"


def test_submit_mfa_without_pending_raises():
    with pytest.raises(garmin_auth.AuthError) as exc:
        garmin_auth.submit_mfa("123456")
    assert exc.value.code == "no_pending_login"


def test_submit_mfa_success_dumps_and_clears(monkeypatch):
    client = FakeClient()
    garmin_auth._pending["client_state"] = {"client": client}
    _patch_garth(monkeypatch, resume=lambda state, code: ("tok1", "tok2"))
    res = garmin_auth.submit_mfa("123456")
    assert res == {"status": "connected"}
    assert client.dumped_to == garmin_auth.TOKENSTORE
    assert (client.oauth1_token, client.oauth2_token) == ("tok1", "tok2")
    assert garmin_auth._pending == {}


def test_submit_mfa_bad_code_keeps_pending_for_retry(monkeypatch):
    garmin_auth._pending["client_state"] = {"client": FakeClient()}

    def boom(state, code):
        raise RuntimeError("401 Client Error")

    _patch_garth(monkeypatch, resume=boom)
    with pytest.raises(garmin_auth.AuthError) as exc:
        garmin_auth.submit_mfa("000000")
    assert exc.value.code == "bad_mfa_code"
    assert "client_state" in garmin_auth._pending  # second attempt possible


# -- API layer: status codes and no credential leakage --------------------------

def test_endpoints_map_auth_errors(monkeypatch):
    from fastapi.testclient import TestClient

    import main

    def deny(email, password):
        raise garmin_auth.AuthError("bad_credentials")

    monkeypatch.setattr(garmin_auth, "start_login", deny)
    client = TestClient(main.app)
    resp = client.post("/api/garmin/login",
                       json={"email": "a@b.c", "password": "hunter2"})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "bad_credentials"}
    assert "hunter2" not in resp.text

    resp = client.post("/api/garmin/mfa", json={"code": "123456"})
    assert resp.status_code == 409
    assert resp.json() == {"detail": "no_pending_login"}

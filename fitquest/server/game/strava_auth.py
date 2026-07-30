"""Strava OAuth2 (authorization code + refresh) for the local server.

Why Strava: one integration covers nearly every athlete — Garmin, Apple
Watch, Polar, Suunto, Coros AND phone-only runners all sync to Strava —
which removes FitQuest's watch-ownership requirement.

Setup (once, by the operator): create an API application on
https://www.strava.com/settings/api (Authorization Callback Domain:
localhost) and provide the credentials via the environment
(STRAVA_CLIENT_ID / STRAVA_CLIENT_SECRET) or $FITQUEST_DATA/strava_app.json
({"clientId": ..., "clientSecret": ...}).

Tokens land in $FITQUEST_DATA/strava_tokens.json and refresh themselves.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from .state import DATA_DIR

APP_FILE = DATA_DIR / "strava_app.json"
TOKEN_FILE = DATA_DIR / "strava_tokens.json"

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
SCOPE = "activity:read_all"


class StravaAuthError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _app_credentials() -> Optional[Dict[str, str]]:
    cid = os.getenv("STRAVA_CLIENT_ID")
    secret = os.getenv("STRAVA_CLIENT_SECRET")
    if cid and secret:
        return {"clientId": cid, "clientSecret": secret}
    if APP_FILE.exists():
        data = json.loads(APP_FILE.read_text())
        if data.get("clientId") and data.get("clientSecret"):
            return data
    return None


def _load_tokens() -> Optional[Dict[str, Any]]:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return None


def _save_tokens(tokens: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_at": tokens["expires_at"],
    }))


def status() -> Dict[str, bool]:
    return {"configured": _app_credentials() is not None,
            "connected": _load_tokens() is not None}


def authorize_url(redirect_uri: str) -> str:
    creds = _app_credentials()
    if creds is None:
        raise StravaAuthError("not_configured")
    from urllib.parse import urlencode

    return AUTHORIZE_URL + "?" + urlencode({
        "client_id": creds["clientId"],
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPE,
        "approval_prompt": "auto",
    })


def exchange_code(code: str) -> Dict[str, bool]:
    """OAuth step 2: authorization code → tokens (persisted)."""
    creds = _app_credentials()
    if creds is None:
        raise StravaAuthError("not_configured")
    import requests

    resp = requests.post(TOKEN_URL, data={
        "client_id": creds["clientId"],
        "client_secret": creds["clientSecret"],
        "code": code,
        "grant_type": "authorization_code",
    }, timeout=20)
    if resp.status_code != 200:
        raise StravaAuthError("exchange_failed")
    _save_tokens(resp.json())
    return {"connected": True}


def access_token() -> str:
    """Valid access token, refreshing transparently when expired."""
    tokens = _load_tokens()
    if tokens is None:
        raise StravaAuthError("not_connected")
    if tokens.get("expires_at", 0) > time.time() + 60:
        return tokens["access_token"]
    creds = _app_credentials()
    if creds is None:
        raise StravaAuthError("not_configured")
    import requests

    resp = requests.post(TOKEN_URL, data={
        "client_id": creds["clientId"],
        "client_secret": creds["clientSecret"],
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token",
    }, timeout=20)
    if resp.status_code != 200:
        raise StravaAuthError("refresh_failed")
    fresh = resp.json()
    _save_tokens(fresh)
    return fresh["access_token"]

"""In-app Garmin SSO login with two-step MFA (garth 0.8.0).

The onboarding screen posts credentials to the local FitQuest server,
which drives garth's SSO flow and stores the OAuth tokens in
$GARMINTOKENS (default ~/.garminconnect) — the same store the provider
and garmin_login.py use. The password is used for the single SSO call
and is never logged, persisted, or echoed back in error details.

garth's client keeps live session state (cookies pinned to the SSO
backend) and is not picklable, so the pending-MFA state lives in a
module-level dict. FitQuest is single-user by design; if uvicorn
restarts between the two steps the caller gets a clean
`no_pending_login` and simply re-submits credentials.

NB: garth is archived upstream — the login/resume_login API used here
is frozen, which is also why it is safe to depend on.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

TOKENSTORE = os.getenv("GARMINTOKENS", "~/.garminconnect")

_pending: Dict[str, Any] = {}


class AuthError(Exception):
    """Login failure with a machine-readable code for the API layer."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _map_exc(exc: Exception, mfa_step: bool = False) -> AuthError:
    text = str(exc)
    if "429" in text:
        return AuthError("rate_limited")
    if "401" in text or "403" in text or "INVALID_USERNAME_PASSWORD" in text:
        return AuthError("bad_mfa_code" if mfa_step else "bad_credentials")
    return AuthError("garmin_error")


def token_status() -> Dict[str, Any]:
    """Whether reusable tokens already exist (no network call)."""
    store = Path(TOKENSTORE).expanduser()
    if not store.exists():
        return {"connected": False}
    try:
        from garth.http import Client

        Client().load(str(store))
        return {"connected": True}
    except Exception:
        return {"connected": False}


def start_login(email: str, password: str) -> Dict[str, str]:
    """Step 1: submit credentials. Returns connected or mfa_required."""
    from garth import sso
    from garth.http import Client

    client = Client()
    try:
        result = sso.login(email, password, client=client,
                           return_on_mfa=True, prompt_mfa=None)
    except Exception as exc:
        raise _map_exc(exc) from None

    if isinstance(result, tuple) and result[0] == "needs_mfa":
        state = result[1]
        _pending["client_state"] = state
        return {"status": "mfa_required",
                "mfaMethod": state.get("mfa_method", "email")}

    client.oauth1_token, client.oauth2_token = result
    client.dump(TOKENSTORE)
    _pending.clear()
    return {"status": "connected"}


def submit_mfa(code: str) -> Dict[str, str]:
    """Step 2: submit the MFA code from step 1's pending state."""
    from garth import sso

    state = _pending.get("client_state")
    if state is None:
        raise AuthError("no_pending_login")
    try:
        oauth1, oauth2 = sso.resume_login(state, code.strip())
    except Exception as exc:
        # keep _pending: a mistyped code can be retried
        raise _map_exc(exc, mfa_step=True) from None

    client = state["client"]
    client.oauth1_token, client.oauth2_token = oauth1, oauth2
    client.dump(TOKENSTORE)
    _pending.clear()
    return {"status": "connected"}

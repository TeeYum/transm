"""Spotify OAuth PKCE authentication for playback control and metadata."""

from __future__ import annotations

import hashlib
import http.server
import json
import logging
import os
import secrets
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_TOKEN_PATH = Path.home() / ".config" / "transm" / "spotify.json"
_REDIRECT_PORT = 8765
_REDIRECT_URI = f"http://localhost:{_REDIRECT_PORT}/callback"
_AUTH_URL = "https://accounts.spotify.com/authorize"
_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SCOPES = "user-read-playback-state user-modify-playback-state user-read-currently-playing"


def _get_client_id() -> str:
    """Get Spotify client ID from environment."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    if not client_id:
        msg = (
            "SPOTIFY_CLIENT_ID not set. "
            "Set it in your environment or .env file."
        )
        raise RuntimeError(msg)
    return client_id


def get_access_token() -> str:
    """Return a valid Spotify access token, refreshing or logging in as needed."""
    token_data = _load_token()
    if token_data:
        # Try using the existing access token
        if _test_token(token_data.get("access_token", "")):
            return token_data["access_token"]
        # Try refreshing
        if "refresh_token" in token_data:
            new_data = _refresh(token_data["refresh_token"])
            if new_data:
                _save_token(new_data)
                return new_data["access_token"]
    msg = "No valid Spotify token. Run 'transm capture --login' first."
    raise RuntimeError(msg)


def login() -> str:
    """Run the full PKCE OAuth flow (opens browser). Returns access token."""
    client_id = _get_client_id()
    verifier = secrets.token_urlsafe(64)
    challenge = (
        hashlib.sha256(verifier.encode())
        .digest()
    )
    import base64

    challenge_b64 = base64.urlsafe_b64encode(challenge).rstrip(b"=").decode()

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": _REDIRECT_URI,
        "scope": _SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge_b64,
    }
    auth_url = f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"

    # Start local server to catch the callback
    code_holder: dict[str, str] = {}

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = urllib.parse.urlparse(self.path).query
            qs = urllib.parse.parse_qs(query)
            if "code" in qs:
                code_holder["code"] = qs["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authenticated! You can close this tab.</h1>")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Authentication failed.")

        def log_message(self, format: str, *args: object) -> None:
            pass  # Suppress server logs

    server = http.server.HTTPServer(("localhost", _REDIRECT_PORT), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request, daemon=True)
    server_thread.start()

    logger.info("Opening browser for Spotify login...")
    webbrowser.open(auth_url)
    server_thread.join(timeout=120)
    server.server_close()

    if "code" not in code_holder:
        msg = "Did not receive auth code from Spotify."
        raise RuntimeError(msg)

    # Exchange code for tokens
    resp = requests.post(
        _TOKEN_URL,
        data={
            "client_id": client_id,
            "grant_type": "authorization_code",
            "code": code_holder["code"],
            "redirect_uri": _REDIRECT_URI,
            "code_verifier": verifier,
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()
    _save_token(token_data)
    logger.info("Spotify authentication successful.")
    return token_data["access_token"]


def _refresh(refresh_token: str) -> dict | None:
    """Refresh an access token using the refresh token."""
    try:
        client_id = _get_client_id()
        resp = requests.post(
            _TOKEN_URL,
            data={
                "client_id": client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        # Preserve refresh token if not returned
        if "refresh_token" not in data:
            data["refresh_token"] = refresh_token
        return data
    except Exception:
        logger.warning("Failed to refresh Spotify token.")
        return None


def _test_token(token: str) -> bool:
    """Quick check if a token is still valid."""
    if not token:
        return False
    try:
        resp = requests.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _load_token() -> dict | None:
    """Load cached token data from disk."""
    if _TOKEN_PATH.exists():
        try:
            return json.loads(_TOKEN_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_token(data: dict) -> None:
    """Save token data to disk."""
    _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_PATH.write_text(json.dumps(data, indent=2))
    _TOKEN_PATH.chmod(0o600)

"""
GitHub OAuth Device Flow authentication for Copilot.

Implements the three-layer token architecture:
  1. GitHub OAuth token (persistent, one-time setup)
  2. Copilot JWT (short-lived, auto-refreshed)
  3. Local usage only (no third-party auth needed)

Based on reverse engineering from github.com/nocoo/raven.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

from .config import CopilotConfig

# Default token storage location
TOKEN_DIR = Path.home() / ".copilot-computer-use"
GITHUB_TOKEN_FILE = TOKEN_DIR / "github_token"
COPILOT_TOKEN_FILE = TOKEN_DIR / "copilot_token"


class CopilotAuth:
    """Handles GitHub OAuth Device Flow and Copilot JWT management."""

    def __init__(self, config: CopilotConfig | None = None):
        self.config = config or CopilotConfig()
        self._github_token: str | None = None
        self._copilot_token: str | None = None
        self._copilot_expires_at: float = 0
        self._load_saved_tokens()

    def _load_saved_tokens(self) -> None:
        """Load previously saved tokens from disk."""
        if GITHUB_TOKEN_FILE.exists():
            self._github_token = GITHUB_TOKEN_FILE.read_text().strip()
        if COPILOT_TOKEN_FILE.exists():
            try:
                data = json.loads(COPILOT_TOKEN_FILE.read_text())
                self._copilot_token = data.get("token")
                self._copilot_expires_at = data.get("expires_at", 0)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_github_token(self, token: str) -> None:
        """Persist GitHub OAuth token to disk."""
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        GITHUB_TOKEN_FILE.write_text(token)
        GITHUB_TOKEN_FILE.chmod(0o600)

    def _save_copilot_token(self, token: str, expires_at: float) -> None:
        """Persist Copilot JWT to disk."""
        TOKEN_DIR.mkdir(parents=True, exist_ok=True)
        COPILOT_TOKEN_FILE.write_text(json.dumps({
            "token": token,
            "expires_at": expires_at,
        }))
        COPILOT_TOKEN_FILE.chmod(0o600)

    def device_flow_login(self) -> str:
        """Run GitHub OAuth Device Flow (interactive, one-time).

        Returns:
            GitHub OAuth access token.
        """
        print("Starting GitHub OAuth Device Flow...")
        print()

        # Step 1: Request device code
        resp = httpx.post(
            self.config.device_code_url,
            data={
                "client_id": self.config.github_client_id,
                "scope": "read:user",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        device_code = data["device_code"]
        user_code = data["user_code"]
        verification_uri = data["verification_uri"]
        interval = data.get("interval", 5) + 1  # Add 1s buffer like Raven

        # Step 2: Show user code
        print(f"  1. Open:  {verification_uri}")
        print(f"  2. Enter: {user_code}")
        print()
        print("Waiting for authorization...")

        # Step 3: Poll for access token
        while True:
            time.sleep(interval)
            resp = httpx.post(
                self.config.access_token_url,
                data={
                    "client_id": self.config.github_client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            result = resp.json()

            if "access_token" in result:
                token = result["access_token"]
                self._github_token = token
                self._save_github_token(token)
                print("Authorization successful!")
                return token

            error = result.get("error")
            if error == "authorization_pending":
                continue
            elif error == "slow_down":
                interval += 5
                continue
            elif error == "expired_token":
                print("Device code expired. Please try again.")
                sys.exit(1)
            elif error == "access_denied":
                print("Authorization denied by user.")
                sys.exit(1)
            else:
                print(f"Unexpected error: {error}")
                sys.exit(1)

    def get_copilot_token(self) -> str:
        """Get a valid Copilot JWT, refreshing if needed.

        Returns:
            Copilot JWT bearer token.

        Raises:
            RuntimeError: If no GitHub token is available.
        """
        # Check if current token is still valid (with 60s buffer)
        if self._copilot_token and time.time() < (self._copilot_expires_at - 60):
            return self._copilot_token

        # Need to refresh
        if not self._github_token:
            raise RuntimeError(
                "No GitHub token found. Run `python -m src.copilot.auth` first."
            )

        return self._refresh_copilot_token()

    def _refresh_copilot_token(self) -> str:
        """Refresh the Copilot JWT using the GitHub OAuth token.

        Returns:
            Fresh Copilot JWT.
        """
        resp = httpx.get(
            self.config.copilot_token_url,
            headers=self.config.get_github_headers(self._github_token),
        )
        resp.raise_for_status()
        data = resp.json()

        token = data["token"]
        expires_at = data["expires_at"]

        self._copilot_token = token
        self._copilot_expires_at = expires_at
        self._save_copilot_token(token, expires_at)

        return token

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid GitHub token."""
        return self._github_token is not None


# CLI entrypoint for standalone auth
if __name__ == "__main__":
    auth = CopilotAuth()
    if auth.is_authenticated:
        print("Already authenticated with GitHub.")
        try:
            token = auth.get_copilot_token()
            print(f"Copilot token valid (expires_at: {auth._copilot_expires_at})")
        except Exception as e:
            print(f"Token refresh failed: {e}")
            print("Re-authenticating...")
            auth.device_flow_login()
    else:
        auth.device_flow_login()

    # Verify the full flow
    try:
        token = auth.get_copilot_token()
        print(f"\nCopilot JWT obtained successfully!")
        print(f"Token prefix: {token[:20]}...")
    except Exception as e:
        print(f"Failed to get Copilot token: {e}")
        sys.exit(1)

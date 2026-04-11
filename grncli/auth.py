from __future__ import annotations

import base64
import time

import httpx

IAM_TOKEN_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"


class TokenManager:
    """OAuth2 Client Credentials token manager with auto-refresh."""

    def __init__(self, client_id: str, client_secret: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token: str | None = None
        self._expires_at: float = 0

    def get_token(self) -> str:
        if self._access_token and time.time() < self._expires_at:
            return self._access_token
        return self._fetch_token()

    def refresh_token(self) -> str:
        self._access_token = None
        self._expires_at = 0
        return self._fetch_token()

    def _fetch_token(self) -> str:
        credentials = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        response = httpx.post(
            IAM_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grantType": "client_credentials"},
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"IAM authentication error (HTTP {response.status_code}): "
                f"{response.text}"
            )

        data = response.json()
        self._access_token = data["accessToken"]
        expires_in = data.get("expiresIn", 1800)
        self._expires_at = time.time() + expires_in - 60
        return self._access_token

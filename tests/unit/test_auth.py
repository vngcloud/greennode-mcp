from __future__ import annotations

import base64
import time

import httpx
import pytest
import respx

from grncli.auth import TokenManager

IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"


class TestTokenManager:
    @respx.mock
    def test_fetch_token(self):
        respx.post(IAM_URL).mock(return_value=httpx.Response(
            200,
            json={
                "accessToken": "test-token-123",
                "token_type": "Bearer",
                "expiresIn": 3600,
            },
        ))

        tm = TokenManager(client_id="my-id", client_secret="my-secret")
        token = tm.get_token()
        assert token == "test-token-123"

    @respx.mock
    def test_token_cached(self):
        route = respx.post(IAM_URL).mock(return_value=httpx.Response(
            200,
            json={
                "accessToken": "test-token-123",
                "token_type": "Bearer",
                "expiresIn": 3600,
            },
        ))

        tm = TokenManager(client_id="my-id", client_secret="my-secret")
        tm.get_token()
        tm.get_token()
        assert route.call_count == 1

    @respx.mock
    def test_refresh_token(self):
        route = respx.post(IAM_URL).mock(return_value=httpx.Response(
            200,
            json={
                "accessToken": "new-token",
                "token_type": "Bearer",
                "expiresIn": 3600,
            },
        ))

        tm = TokenManager(client_id="my-id", client_secret="my-secret")
        token = tm.refresh_token()
        assert token == "new-token"

    @respx.mock
    def test_basic_auth_header(self):
        route = respx.post(IAM_URL).mock(return_value=httpx.Response(
            200,
            json={
                "accessToken": "tok",
                "token_type": "Bearer",
                "expiresIn": 3600,
            },
        ))

        tm = TokenManager(client_id="my-id", client_secret="my-secret")
        tm.get_token()

        request = route.calls[0].request
        expected = base64.b64encode(b"my-id:my-secret").decode()
        assert request.headers["authorization"] == f"Basic {expected}"

    @respx.mock
    def test_auth_failure_raises(self):
        respx.post(IAM_URL).mock(return_value=httpx.Response(
            401,
            json={"error": "invalid_client"},
        ))

        tm = TokenManager(client_id="bad-id", client_secret="bad-secret")
        with pytest.raises(Exception, match="401"):
            tm.get_token()

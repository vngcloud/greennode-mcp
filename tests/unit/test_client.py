from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from grncli.client import GreenodeClient


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.get_endpoint.return_value = "https://vks.api.vngcloud.vn"
    tm = MagicMock()
    tm.get_token.return_value = "test-token"
    tm.refresh_token.return_value = "refreshed-token"
    session.get_token_manager.return_value = tm
    return session


class TestGreenodeClient:
    @respx.mock
    def test_get_request(self, mock_session):
        route = respx.get("https://vks.api.vngcloud.vn/v1/clusters").mock(
            return_value=httpx.Response(200, json={"items": []})
        )

        client = GreenodeClient(mock_session, "vks")
        result = client.get("/v1/clusters")
        assert result == {"items": []}
        assert route.calls[0].request.headers["authorization"] == "Bearer test-token"

    @respx.mock
    def test_post_request(self, mock_session):
        respx.post("https://vks.api.vngcloud.vn/v1/clusters").mock(
            return_value=httpx.Response(202, json={"id": "new-id"})
        )

        client = GreenodeClient(mock_session, "vks")
        result = client.post("/v1/clusters", json={"name": "test"})
        assert result == {"id": "new-id"}

    @respx.mock
    def test_401_triggers_refresh_and_retry(self, mock_session):
        route = respx.get("https://vks.api.vngcloud.vn/v1/clusters")
        route.side_effect = [
            httpx.Response(401, json={"error": "expired"}),
            httpx.Response(200, json={"items": []}),
        ]

        client = GreenodeClient(mock_session, "vks")
        result = client.get("/v1/clusters")
        assert result == {"items": []}
        mock_session.get_token_manager().refresh_token.assert_called_once()

    @respx.mock
    def test_get_raw(self, mock_session):
        respx.get("https://vks.api.vngcloud.vn/v1/clusters/abc/kubeconfig").mock(
            return_value=httpx.Response(200, text="apiVersion: v1\nkind: Config")
        )

        client = GreenodeClient(mock_session, "vks")
        result = client.get_raw("/v1/clusters/abc/kubeconfig")
        assert "apiVersion" in result

    @respx.mock
    def test_error_response_raises(self, mock_session):
        respx.get("https://vks.api.vngcloud.vn/v1/clusters/bad").mock(
            return_value=httpx.Response(404, json={"message": "Not found"})
        )

        client = GreenodeClient(mock_session, "vks")
        with pytest.raises(RuntimeError, match="404"):
            client.get("/v1/clusters/bad")

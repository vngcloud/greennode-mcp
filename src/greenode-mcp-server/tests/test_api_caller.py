"""Tests for api_caller — call_api tool implementation."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from greennode.greenode_mcp_server.api_caller import (
    _format_list,
    _format_object,
    _format_response,
    call_api,
)
from greennode.greenode_mcp_server.api_index import (
    EndpointEntry,
    reset_index,
    set_index,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_index()
    # Initialize with a minimal VKS spec for testing
    set_index([
        EndpointEntry(
            product="vks",
            method="GET",
            path="/v1/clusters",
            summary="List clusters",
            description="",
            servers={"HCM-3": "https://vks.api.vngcloud.vn", "HAN": "https://vks.api.vngcloud.vn"},
        ),
        EndpointEntry(
            product="vks",
            method="POST",
            path="/v1/clusters",
            summary="Create cluster",
            description="",
            servers={"HCM-3": "https://vks.api.vngcloud.vn", "HAN": "https://vks.api.vngcloud.vn"},
        ),
        EndpointEntry(
            product="vks",
            method="DELETE",
            path="/v1/clusters/{cluster_id}",
            summary="Delete cluster",
            description="",
            servers={"HCM-3": "https://vks.api.vngcloud.vn", "HAN": "https://vks.api.vngcloud.vn"},
        ),
    ])
    yield
    reset_index()


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.default_region = "HCM-3"
    endpoints = MagicMock()
    endpoints.vks = "https://vks.api.vngcloud.vn"
    config.get_endpoints.return_value = endpoints
    return config


@pytest.fixture
def mock_token_manager():
    tm = MagicMock()
    tm.get_token = AsyncMock(return_value="test-token")
    return tm


async def _call(
    method, path, *, config, token_manager, allow_write=True,
    product=None, region=None, params=None, body=None,
):
    return await call_api(
        method, path, product, region, params, body,
        config, token_manager, allow_write,
    )


# --- Write guard ---

async def test_write_guard_blocks_post_when_not_allowed(mock_config, mock_token_manager):
    result = await _call(
        "POST", "/v1/clusters",
        config=mock_config, token_manager=mock_token_manager, allow_write=False,
    )
    assert "write operation" in result.lower()
    assert "--allow-write" in result


async def test_write_guard_blocks_delete_when_not_allowed(mock_config, mock_token_manager):
    result = await _call(
        "DELETE", "/v1/clusters/abc",
        config=mock_config, token_manager=mock_token_manager, allow_write=False,
    )
    assert "write operation" in result.lower()


async def test_write_guard_allows_get_always(mock_config, mock_token_manager):
    with respx.mock:
        respx.get("https://vks.api.vngcloud.vn/v1/clusters").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        result = await _call(
            "GET", "/v1/clusters",
            config=mock_config, token_manager=mock_token_manager, allow_write=False,
        )
    assert "No items found" in result


async def test_write_guard_allows_post_when_enabled(mock_config, mock_token_manager):
    with respx.mock:
        respx.post("https://vks.api.vngcloud.vn/v1/clusters").mock(
            return_value=httpx.Response(202, json={"uid": "abc123", "name": "my-cluster"})
        )
        result = await _call(
            "POST", "/v1/clusters",
            config=mock_config, token_manager=mock_token_manager, allow_write=True,
        )
    assert "202" in result or "accepted" in result.lower()


# --- Path validation ---

async def test_path_must_start_with_slash(mock_config, mock_token_manager):
    result = await _call(
        "GET", "v1/clusters",
        config=mock_config, token_manager=mock_token_manager,
    )
    assert "Error" in result
    assert "start with '/'" in result


async def test_path_traversal_rejected(mock_config, mock_token_manager):
    result = await _call(
        "GET", "/v1/../etc/passwd",
        config=mock_config, token_manager=mock_token_manager,
    )
    assert "traversal" in result.lower()


# --- Auth injection ---

async def test_bearer_token_injected(mock_config, mock_token_manager):
    with respx.mock:
        route = respx.get("https://vks.api.vngcloud.vn/v1/clusters").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        await _call("GET", "/v1/clusters", config=mock_config, token_manager=mock_token_manager)
    assert route.called
    assert route.calls[0].request.headers["authorization"] == "Bearer test-token"


# --- Response formatting ---

def test_format_list_with_dicts():
    items = [{"name": "c1", "status": "ACTIVE"}, {"name": "c2", "status": "CREATING"}]
    result = _format_list(items)
    assert "name" in result
    assert "c1" in result
    assert "|" in result  # markdown table


def test_format_list_empty():
    assert "No items found" in _format_list([])


def test_format_object():
    result = _format_object({"uid": "abc", "name": "test"})
    assert "uid" in result
    assert "abc" in result


def test_format_response_with_items_key():
    data = {"items": [{"name": "c1"}], "total": 1}
    result = _format_response(data)
    assert "c1" in result


def test_format_response_plain_object():
    result = _format_response({"uid": "abc"})
    assert "uid" in result


def test_format_response_list():
    result = _format_response([{"name": "item1"}])
    assert "item1" in result


# --- HTTP responses ---

async def test_404_error_returned_as_message(mock_config, mock_token_manager):
    with respx.mock:
        respx.get("https://vks.api.vngcloud.vn/v1/clusters").mock(
            return_value=httpx.Response(404, json={"message": "cluster not found"})
        )
        result = await _call("GET", "/v1/clusters", config=mock_config, token_manager=mock_token_manager)
    assert "404" in result
    assert "cluster not found" in result


async def test_204_no_content_returns_success_message(mock_config, mock_token_manager):
    with respx.mock:
        respx.delete("https://vks.api.vngcloud.vn/v1/clusters/abc").mock(
            return_value=httpx.Response(204)
        )
        result = await _call(
            "DELETE", "/v1/clusters/abc",
            config=mock_config, token_manager=mock_token_manager, allow_write=True,
        )
    assert "success" in result.lower() or "completed" in result.lower()


async def test_timeout_returns_error_message(mock_config, mock_token_manager):
    with respx.mock:
        respx.get("https://vks.api.vngcloud.vn/v1/clusters").mock(
            side_effect=httpx.ConnectTimeout("timeout")
        )
        result = await _call("GET", "/v1/clusters", config=mock_config, token_manager=mock_token_manager)
    assert "timed out" in result.lower()

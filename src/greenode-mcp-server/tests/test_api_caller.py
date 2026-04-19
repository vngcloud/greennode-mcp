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
    config.default_project_id = None
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
    assert "**uid**" in result  # multi-field still uses bold


def test_format_object_single_field_uses_plain_format():
    """Single-field responses avoid markdown bold noise."""
    result = _format_object({"status": "DELETING"})
    assert result == "status: DELETING"
    assert "**" not in result


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


def test_format_response_listData_key_vserver_style():
    """vServer APIs wrap lists under 'listData' key, not 'items'."""
    data = {"listData": [{"id": "sg-1", "name": "secgroup-1"}], "total": 1}
    result = _format_response(data)
    assert "sg-1" in result
    assert "|" in result  # markdown table, not object dump


def test_format_response_data_key():
    data = {"data": [{"name": "x"}]}
    result = _format_response(data)
    assert "x" in result
    assert "|" in result


def test_format_response_results_key():
    data = {"results": [{"name": "y"}]}
    result = _format_response(data)
    assert "y" in result


def test_format_list_truncates_long_lists():
    items = [{"id": i, "name": f"item-{i}"} for i in range(100)]
    result = _format_list(items)
    # Only first 30 shown
    assert "item-0" in result
    assert "item-29" in result
    assert "item-30" not in result
    # Truncation footer present
    assert "Showing 30 of 100" in result


def test_format_list_no_truncation_footer_when_small():
    items = [{"id": i} for i in range(10)]
    result = _format_list(items)
    assert "Showing" not in result


def test_format_list_scalar_items_truncated():
    items = [f"str-{i}" for i in range(50)]
    result = _format_list(items)
    assert "str-0" in result
    assert "str-29" in result
    assert "str-30" not in result
    assert "Showing 30 of 50" in result


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


# --- project_id auto-substitution ---

async def test_project_id_placeholder_substituted(mock_config, mock_token_manager):
    pc = MagicMock()
    pc.get_project_id = AsyncMock(return_value="pro-abc")
    with respx.mock:
        route = respx.get("https://vks.api.vngcloud.vn/v2/pro-abc/networks").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        await call_api(
            "GET", "/v2/{projectId}/networks", None, None, None, None,
            mock_config, mock_token_manager, False, project_context=pc,
        )
    assert route.called
    pc.get_project_id.assert_called_once()


async def test_project_id_snake_case_placeholder_substituted(mock_config, mock_token_manager):
    pc = MagicMock()
    pc.get_project_id = AsyncMock(return_value="pro-xyz")
    with respx.mock:
        route = respx.get("https://vks.api.vngcloud.vn/v1/pro-xyz/flavors").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        await call_api(
            "GET", "/v1/{project_id}/flavors", None, None, None, None,
            mock_config, mock_token_manager, False, project_context=pc,
        )
    assert route.called


async def test_no_substitution_when_placeholder_absent(mock_config, mock_token_manager):
    pc = MagicMock()
    pc.get_project_id = AsyncMock(return_value="pro-abc")
    with respx.mock:
        respx.get("https://vks.api.vngcloud.vn/v1/clusters").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        await call_api(
            "GET", "/v1/clusters", None, None, None, None,
            mock_config, mock_token_manager, False, project_context=pc,
        )
    pc.get_project_id.assert_not_called()


async def test_project_id_fetch_failure_returns_error(mock_config, mock_token_manager):
    pc = MagicMock()
    pc.get_project_id = AsyncMock(side_effect=RuntimeError("no projects"))
    result = await call_api(
        "GET", "/v2/{projectId}/networks", None, None, None, None,
        mock_config, mock_token_manager, False, project_context=pc,
    )
    assert "failed to resolve project_id" in result.lower()
    assert "no projects" in result


async def test_config_project_id_preferred_over_context(mock_config, mock_token_manager):
    """When config has a default_project_id, skip the API fetch."""
    mock_config.default_project_id = "pro-from-config"
    pc = MagicMock()
    pc.get_project_id = AsyncMock(return_value="pro-from-api")
    with respx.mock:
        route = respx.get("https://vks.api.vngcloud.vn/v2/pro-from-config/networks").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        await call_api(
            "GET", "/v2/{projectId}/networks", None, None, None, None,
            mock_config, mock_token_manager, False, project_context=pc,
        )
    assert route.called
    pc.get_project_id.assert_not_called()


async def test_context_fallback_when_config_project_id_empty(mock_config, mock_token_manager):
    """Fallback: when config has no project_id, use ProjectContext."""
    mock_config.default_project_id = None
    pc = MagicMock()
    pc.get_project_id = AsyncMock(return_value="pro-from-api")
    with respx.mock:
        route = respx.get("https://vks.api.vngcloud.vn/v2/pro-from-api/networks").mock(
            return_value=httpx.Response(200, json={"items": []})
        )
        await call_api(
            "GET", "/v2/{projectId}/networks", None, None, None, None,
            mock_config, mock_token_manager, False, project_context=pc,
        )
    assert route.called
    pc.get_project_id.assert_called_once()


async def test_no_project_id_anywhere_returns_error(mock_config, mock_token_manager):
    """When neither config nor context can resolve, return actionable error."""
    mock_config.default_project_id = None
    result = await call_api(
        "GET", "/v2/{projectId}/networks", None, None, None, None,
        mock_config, mock_token_manager, False, project_context=None,
    )
    assert "project_id not configured" in result
    assert "grn configure" in result
    assert "GRN_DEFAULT_PROJECT_ID" in result

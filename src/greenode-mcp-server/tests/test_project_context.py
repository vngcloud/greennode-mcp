"""Tests for ProjectContext — auto-fetch and cache project_id."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from greennode.greenode_mcp_server.project_context import ProjectContext


VSERVER_BASE = "https://vserver.example"


def _make_config(vserver_url: str = VSERVER_BASE):
    config = MagicMock()
    config.default_region = "HCM-3"
    endpoints = MagicMock()
    endpoints.vserver = vserver_url
    config.get_endpoints.return_value = endpoints
    return config


def _make_tm(token: str = "tok"):
    tm = MagicMock()
    tm.get_token = AsyncMock(return_value=token)
    return tm


@pytest.mark.asyncio
async def test_fetches_and_returns_first_project_id():
    ctx = ProjectContext(_make_config(), _make_tm())
    with respx.mock:
        respx.get(f"{VSERVER_BASE}/v1/projects").mock(
            return_value=httpx.Response(200, json={"projects": [{"projectId": "pro-abc", "userId": 1}]}),
        )
        pid = await ctx.get_project_id()
    assert pid == "pro-abc"


@pytest.mark.asyncio
async def test_caches_after_first_call():
    ctx = ProjectContext(_make_config(), _make_tm())
    with respx.mock:
        route = respx.get(f"{VSERVER_BASE}/v1/projects").mock(
            return_value=httpx.Response(200, json={"projects": [{"projectId": "pro-x"}]}),
        )
        await ctx.get_project_id()
        await ctx.get_project_id()
        await ctx.get_project_id()
    assert route.call_count == 1


@pytest.mark.asyncio
async def test_uses_first_when_account_has_multiple_projects():
    ctx = ProjectContext(_make_config(), _make_tm())
    with respx.mock:
        respx.get(f"{VSERVER_BASE}/v1/projects").mock(
            return_value=httpx.Response(200, json={
                "projects": [
                    {"projectId": "pro-first"},
                    {"projectId": "pro-second"},
                ]
            }),
        )
        pid = await ctx.get_project_id()
    assert pid == "pro-first"


@pytest.mark.asyncio
async def test_raises_when_no_projects():
    ctx = ProjectContext(_make_config(), _make_tm())
    with respx.mock:
        respx.get(f"{VSERVER_BASE}/v1/projects").mock(
            return_value=httpx.Response(200, json={"projects": []}),
        )
        with pytest.raises(RuntimeError, match="no projects"):
            await ctx.get_project_id()


@pytest.mark.asyncio
async def test_raises_on_http_error():
    ctx = ProjectContext(_make_config(), _make_tm())
    with respx.mock:
        respx.get(f"{VSERVER_BASE}/v1/projects").mock(
            return_value=httpx.Response(500),
        )
        with pytest.raises(RuntimeError, match="HTTP 500"):
            await ctx.get_project_id()


@pytest.mark.asyncio
async def test_raises_on_network_error():
    ctx = ProjectContext(_make_config(), _make_tm())
    with respx.mock:
        respx.get(f"{VSERVER_BASE}/v1/projects").mock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(RuntimeError, match="Failed to fetch"):
            await ctx.get_project_id()


@pytest.mark.asyncio
async def test_cached_project_id_returns_none_before_fetch():
    ctx = ProjectContext(_make_config(), _make_tm())
    assert ctx.cached_project_id() is None


@pytest.mark.asyncio
async def test_cached_project_id_returns_value_after_fetch():
    ctx = ProjectContext(_make_config(), _make_tm())
    with respx.mock:
        respx.get(f"{VSERVER_BASE}/v1/projects").mock(
            return_value=httpx.Response(200, json={"projects": [{"projectId": "pro-y"}]}),
        )
        await ctx.get_project_id()
    assert ctx.cached_project_id() == "pro-y"

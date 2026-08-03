"""Tests for the Agentbase 1-based paging helper (uses conftest's policy_client)."""

from __future__ import annotations

import httpx
import respx
from greennode.agentbase_mcp_server.paging import fetch_all_agentbase_items


@respx.mock
async def test_pages_until_total_reached(policy_client):
    base = "https://agentbase.api.vngcloud.vn/policy"
    respx.get(f"{base}/items").mock(
        side_effect=[
            httpx.Response(200, json={"items": [{"id": "a"}, {"id": "b"}], "totalItem": 3}),
            httpx.Response(200, json={"items": [{"id": "c"}], "totalItem": 3}),
        ]
    )
    out = await fetch_all_agentbase_items(policy_client, "/items", size=2)
    assert [i["id"] for i in out] == ["a", "b", "c"]
    # Page 1 then page 2 (1-based).
    calls = [c.request.url.params for c in respx.mock.calls]
    assert calls[0]["page"] == "1" and calls[0]["page_size"] == "2"
    assert calls[1]["page"] == "2"


@respx.mock
async def test_single_page_when_total_under_size(policy_client):
    base = "https://agentbase.api.vngcloud.vn/policy"
    respx.get(f"{base}/items").mock(
        return_value=httpx.Response(200, json={"items": [{"id": "a"}], "totalItem": 1})
    )
    out = await fetch_all_agentbase_items(policy_client, "/items", size=10)
    assert out == [{"id": "a"}]
    assert len(respx.mock.calls) == 1

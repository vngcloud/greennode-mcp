"""1-based paging over Agentbase list envelopes.

Agentbase lists use `page` (1-based) + `page_size`, returning
`{items: [...], totalItem: N}`. List tools never expose paging params to the
model — they page internally until totalItem is reached.
"""

from __future__ import annotations

from greennode.agentbase_mcp_server.client import AgentbaseClient
from typing import Any


async def fetch_all_agentbase_items(
    client: AgentbaseClient,
    path: str,
    params: dict[str, Any] | None = None,
    size: int = 10,
) -> list[dict[str, Any]]:
    """Page through an Agentbase list endpoint until all items are collected."""
    collected: list[dict[str, Any]] = []
    page = 1
    base_params = dict(params or {})
    while True:
        query = {**base_params, "page": page, "page_size": size}
        data = await client.get(path, params=query)
        data = data or {}
        items = data.get("items") or data.get("listData") or []
        total = data.get("totalItem") or data.get("total") or len(items)
        collected.extend(items)
        if len(items) < size or len(collected) >= total:
            break
        page += 1
        if page > 1000:  # hard backstop
            break
    return collected

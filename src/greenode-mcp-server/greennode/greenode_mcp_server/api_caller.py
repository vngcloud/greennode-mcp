"""call_api tool — authenticated REST API calls to any VNG Cloud product."""
from __future__ import annotations

import httpx

from greennode.greenode_mcp_server.api_index import get_index
from greennode.greenode_mcp_server.auth import TokenManager
from greennode.greenode_mcp_server.config import VksConfig

DEFAULT_TIMEOUT = 30.0
SAFE_METHODS = frozenset({"GET", "HEAD"})


def _resolve_base_url(path: str, product: str | None, region: str, config: VksConfig) -> str:
    """Find base URL for a path from the spec index.

    Matches by path prefix (handles template paths like /v1/clusters/{id}).
    Falls back to the VKS base URL from config REGIONS dict if no match found.
    """
    for entry in get_index():
        if product and entry.product != product:
            continue
        template_prefix = entry.path.split("{")[0].rstrip("/")
        if path == entry.path or (template_prefix and path.startswith(template_prefix + "/")):
            if region in entry.servers:
                return entry.servers[region]
    # Fallback: VKS base URL from config (covers VKS paths when spec not loaded)
    endpoints = config.get_endpoints(region)
    return endpoints.vks.rstrip("/")


def _format_list(items: list) -> str:
    if not items:
        return "No items found."
    if not isinstance(items[0], dict):
        return "\n".join(f"- {item}" for item in items)
    keys = list(items[0].keys())[:6]
    header = "| " + " | ".join(keys) + " |"
    sep = "|" + "|".join("---" for _ in keys) + "|"
    rows = [
        "| " + " | ".join(str(item.get(k, "")) for k in keys) + " |"
        for item in items
    ]
    return "\n".join([header, sep] + rows)


def _format_object(obj: dict) -> str:
    return "\n".join(f"**{k}**: {v}" for k, v in obj.items())


def _format_response(data) -> str:
    """Best-effort markdown formatting of an API response."""
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return _format_list(items)
        return _format_object(data)
    if isinstance(data, list):
        return _format_list(data)
    return str(data)


async def call_api(
    method: str,
    path: str,
    product: str | None,
    region: str | None,
    params: dict | None,
    body: dict | None,
    config: VksConfig,
    token_manager: TokenManager,
    allow_write: bool,
) -> str:
    """Execute a VNG Cloud REST API call with automatic auth injection."""
    method = method.upper()

    # Write guard
    if method not in SAFE_METHODS and not allow_write:
        return (
            f"Error: {method} {path} is a write operation. "
            "Restart the server with --allow-write to enable write operations."
        )

    # Path validation
    if not path.startswith("/"):
        return f"Error: path must start with '/' (got: {path!r})"
    if ".." in path:
        return "Error: path traversal not allowed"

    resolved_region = region or config.default_region
    base_url = _resolve_base_url(path, product, resolved_region, config)
    url = base_url + path

    token = await token_manager.get_token()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.request(method, url, headers=headers, params=params, json=body)

        if resp.status_code == 204:
            return "Operation completed successfully."

        try:
            data = resp.json()
        except Exception:
            return f"HTTP {resp.status_code}: {resp.text[:500]}"

        if resp.status_code >= 400:
            msg = data.get("message") or data.get("error") or str(data)
            return f"Error {resp.status_code}: {msg}"

        result = _format_response(data)
        if resp.status_code == 202:
            return f"Operation accepted (202).\n{result}"
        return result

    except httpx.TimeoutException:
        return f"Error: request to {url} timed out after {DEFAULT_TIMEOUT}s"
    except httpx.RequestError as exc:
        return f"Error: request failed: {exc}"

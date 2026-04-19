"""RedoclyPortalProvider — scrapes VNG Cloud's docs portal HTML for specs."""
from __future__ import annotations

import json
import re

import httpx

from greennode.greenode_mcp_server._build_info import DEFAULT_DOCS_PORTAL_URL

from .provider import ProductRef, SpecExtractionError, SpecFetchError


LIST_TIMEOUT_SECONDS = 10.0
FETCH_TIMEOUT_SECONDS = 15.0
MAX_HTML_SCAN_BYTES = 5 * 1024 * 1024   # 5 MB cap on HTML scanning
MAX_SPEC_BYTES = 10 * 1024 * 1024       # 10 MB cap on extracted JSON

# Matches <a href="service-docs/<slug>.html">Anchor Text</a>
_LINK_RE = re.compile(
    r'<a\s+[^>]*href=["\']service-docs/([a-z0-9][a-z0-9\-]*)\.html["\'][^>]*>'
    r'([^<]+)</a>',
    re.IGNORECASE,
)

_OPENAPI_MARKER = '"openapi":"3.'


def _slug_to_product_name(slug: str) -> str:
    """Normalize slugs like 'vks-api', 'vlb-api' to 'vks', 'vlb'."""
    if slug.endswith("-api"):
        return slug[: -len("-api")]
    return slug


def _extract_inline_openapi(html: str) -> dict:
    """Find and parse the inline OpenAPI JSON embedded in a Redocly Portal page."""
    if len(html) > MAX_HTML_SCAN_BYTES:
        raise SpecExtractionError("(unknown)", f"HTML exceeds {MAX_HTML_SCAN_BYTES} bytes")

    marker_idx = html.find(_OPENAPI_MARKER)
    if marker_idx < 0:
        raise SpecExtractionError("(unknown)", f"marker {_OPENAPI_MARKER!r} not found")

    start = html.rfind("{", 0, marker_idx)
    if start < 0:
        raise SpecExtractionError("(unknown)", "opening brace not found before marker")

    depth = 0
    in_str = False
    esc = False
    end = -1
    for i in range(start, min(len(html), start + MAX_SPEC_BYTES)):
        c = html[i]
        if esc:
            esc = False
            continue
        if c == "\\":
            esc = True
            continue
        if c == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end < 0:
        raise SpecExtractionError("(unknown)", "unbalanced braces in inline spec")

    blob = html[start:end]
    if len(blob) > MAX_SPEC_BYTES:
        raise SpecExtractionError("(unknown)", f"spec exceeds {MAX_SPEC_BYTES} bytes")

    try:
        spec = json.loads(blob)
    except json.JSONDecodeError as e:
        raise SpecExtractionError("(unknown)", f"JSON parse error: {e}") from e

    if "openapi" not in spec or "paths" not in spec:
        raise SpecExtractionError(
            "(unknown)",
            "parsed JSON missing 'openapi' or 'paths' key",
        )

    return spec


class RedoclyPortalProvider:
    """Fetches OpenAPI specs by scraping VNG Cloud's docs portal."""

    def __init__(self, base_url: str | None = None) -> None:
        # base_url is used only by tests; production builds use DEFAULT_DOCS_PORTAL_URL
        resolved = base_url or DEFAULT_DOCS_PORTAL_URL
        if not resolved.startswith("https://"):
            raise ValueError(f"base_url must be https://: {resolved!r}")
        self.base_url = resolved.rstrip("/")

    def provider_name(self) -> str:
        return "redocly-portal"

    async def list_products(self) -> list[ProductRef]:
        url = self.base_url + "/"
        try:
            async with httpx.AsyncClient(timeout=LIST_TIMEOUT_SECONDS, follow_redirects=True) as c:
                resp = await c.get(url)
        except httpx.HTTPError as e:
            raise SpecFetchError("(landing)", f"network error: {e}") from e

        if resp.status_code != 200:
            raise SpecFetchError("(landing)", f"HTTP {resp.status_code}")

        refs: list[ProductRef] = []
        seen: set[str] = set()
        for match in _LINK_RE.finditer(resp.text):
            slug = match.group(1).lower()
            display = match.group(2).strip()
            name = _slug_to_product_name(slug)
            if name in seen:
                continue
            seen.add(name)
            refs.append(ProductRef(
                name=name,
                display_name=display,
                source_url=f"{self.base_url}/service-docs/{slug}.html",
            ))
        return refs

    async def fetch_spec(self, ref: ProductRef) -> dict:
        headers: dict[str, str] = {}
        if etag := ref.metadata.get("etag"):
            headers["If-None-Match"] = etag
        if lm := ref.metadata.get("last_modified"):
            headers["If-Modified-Since"] = lm

        try:
            async with httpx.AsyncClient(timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True) as c:
                resp = await c.get(ref.source_url, headers=headers)
        except httpx.HTTPError as e:
            raise SpecFetchError(ref.name, f"network error: {e}") from e

        if resp.status_code == 304:
            raise SpecFetchError(ref.name, "HTTP 304 Not Modified (caller should reuse cached body)")
        if resp.status_code != 200:
            raise SpecFetchError(ref.name, f"HTTP {resp.status_code}")

        try:
            spec = _extract_inline_openapi(resp.text)
        except SpecExtractionError as e:
            raise SpecExtractionError(ref.name, e.reason) from e

        # Stash response cache headers on the ref's metadata for the caller to persist
        ref.metadata["etag"] = resp.headers.get("ETag") or ref.metadata.get("etag")
        ref.metadata["last_modified"] = resp.headers.get("Last-Modified") or ref.metadata.get("last_modified")
        return spec

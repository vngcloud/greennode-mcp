"""Tests for RedoclyPortalProvider — scrapes VNG Cloud docs portal HTML."""
from __future__ import annotations

import httpx
import pytest
import respx

from greennode.greenode_mcp_server.registry.provider import (
    ProductRef,
    SpecExtractionError,
    SpecFetchError,
)
from greennode.greenode_mcp_server.registry.redocly_portal import (
    RedoclyPortalProvider,
    _extract_inline_openapi,
)


BASE_URL = "https://fake-portal.example"


LANDING_HTML = """
<!DOCTYPE html>
<html>
<body>
  <nav>
    <a href="service-docs/vks-api.html">VKS-API</a>
    <a href="service-docs/vlb-api.html">vLB-API</a>
    <a href="service-docs/vserver.html">vServer API</a>
    <a href="https://outside.example/other">outside link</a>
    <a href="other/page.html">unrelated</a>
  </nav>
</body>
</html>
"""


VKS_PAGE_HTML = """
<!DOCTYPE html>
<html>
<body>
<script>
var STATE = {"spec":{"openapi":"3.0.3","info":{"title":"VKS API","version":"1.0"},"paths":{"/v1/clusters":{"get":{"summary":"list"}}}}};
</script>
</body>
</html>
"""


# --- _extract_inline_openapi ---

def test_extract_inline_openapi_finds_json():
    spec = _extract_inline_openapi(VKS_PAGE_HTML)
    assert spec["openapi"] == "3.0.3"
    assert "/v1/clusters" in spec["paths"]


def test_extract_inline_openapi_marker_missing_raises():
    with pytest.raises(SpecExtractionError):
        _extract_inline_openapi("<html><body>no spec here</body></html>")


def test_extract_inline_openapi_unbalanced_raises():
    bad = '<script>var x = {"openapi":"3.0.0","paths":{"/a":{"get":{</script>'
    with pytest.raises(SpecExtractionError):
        _extract_inline_openapi(bad)


def test_extract_inline_openapi_missing_paths_key_raises():
    html = '<script>var x = {"openapi":"3.0.0","info":{"title":"X"}};</script>'
    with pytest.raises(SpecExtractionError):
        _extract_inline_openapi(html)


def test_extract_inline_openapi_handles_escaped_quotes_in_strings():
    html = '<script>var s = {"openapi":"3.0.0","info":{"title":"Quoted \\"X\\" "},"paths":{}};</script>'
    spec = _extract_inline_openapi(html)
    assert spec["info"]["title"] == 'Quoted "X" '


# --- list_products ---

@pytest.mark.asyncio
async def test_list_products_scrapes_landing_page():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    with respx.mock:
        respx.get(BASE_URL + "/").mock(return_value=httpx.Response(200, text=LANDING_HTML))
        refs = await p.list_products()
    names = sorted(r.name for r in refs)
    assert names == ["vks", "vlb", "vserver"]


@pytest.mark.asyncio
async def test_list_products_sets_source_url_and_display_name():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    with respx.mock:
        respx.get(BASE_URL + "/").mock(return_value=httpx.Response(200, text=LANDING_HTML))
        refs = await p.list_products()
    vks = next(r for r in refs if r.name == "vks")
    assert vks.source_url == f"{BASE_URL}/service-docs/vks-api.html"
    assert vks.display_name == "VKS-API"


@pytest.mark.asyncio
async def test_list_products_raises_on_network_error():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    with respx.mock:
        respx.get(BASE_URL + "/").mock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(SpecFetchError):
            await p.list_products()


@pytest.mark.asyncio
async def test_list_products_raises_on_http_500():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    with respx.mock:
        respx.get(BASE_URL + "/").mock(return_value=httpx.Response(500))
        with pytest.raises(SpecFetchError):
            await p.list_products()


# --- fetch_spec ---

@pytest.mark.asyncio
async def test_fetch_spec_returns_parsed_json():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    ref = ProductRef(
        name="vks",
        display_name="VKS API",
        source_url=f"{BASE_URL}/service-docs/vks-api.html",
    )
    with respx.mock:
        respx.get(ref.source_url).mock(return_value=httpx.Response(200, text=VKS_PAGE_HTML))
        spec = await p.fetch_spec(ref)
    assert spec["openapi"] == "3.0.3"


@pytest.mark.asyncio
async def test_fetch_spec_sends_conditional_headers_when_metadata_present():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    ref = ProductRef(
        name="vks",
        display_name="VKS API",
        source_url=f"{BASE_URL}/service-docs/vks-api.html",
        metadata={"etag": '"abc"', "last_modified": "Tue, 15 Apr 2026 08:30:00 GMT"},
    )
    with respx.mock:
        route = respx.get(ref.source_url).mock(return_value=httpx.Response(200, text=VKS_PAGE_HTML))
        await p.fetch_spec(ref)
    req = route.calls[0].request
    assert req.headers.get("If-None-Match") == '"abc"'
    assert req.headers.get("If-Modified-Since") == "Tue, 15 Apr 2026 08:30:00 GMT"


@pytest.mark.asyncio
async def test_fetch_spec_304_raises_specific_error():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    ref = ProductRef(
        name="vks",
        display_name="VKS API",
        source_url=f"{BASE_URL}/service-docs/vks-api.html",
        metadata={"etag": '"abc"'},
    )
    with respx.mock:
        respx.get(ref.source_url).mock(return_value=httpx.Response(304))
        with pytest.raises(SpecFetchError) as ei:
            await p.fetch_spec(ref)
    assert "304" in ei.value.reason


@pytest.mark.asyncio
async def test_fetch_spec_http_error_raises():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    ref = ProductRef(name="vks", display_name="VKS API", source_url=f"{BASE_URL}/x.html")
    with respx.mock:
        respx.get(ref.source_url).mock(return_value=httpx.Response(404))
        with pytest.raises(SpecFetchError):
            await p.fetch_spec(ref)


@pytest.mark.asyncio
async def test_fetch_spec_extraction_failure_raises_extraction_error():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    ref = ProductRef(name="vks", display_name="VKS API", source_url=f"{BASE_URL}/x.html")
    with respx.mock:
        respx.get(ref.source_url).mock(return_value=httpx.Response(200, text="<html>empty</html>"))
        with pytest.raises(SpecExtractionError):
            await p.fetch_spec(ref)


def test_provider_name():
    p = RedoclyPortalProvider(base_url=BASE_URL)
    assert p.provider_name() == "redocly-portal"


def test_base_url_defaults_to_build_info():
    from greennode.greenode_mcp_server._build_info import DEFAULT_DOCS_PORTAL_URL
    p = RedoclyPortalProvider()
    assert p.base_url == DEFAULT_DOCS_PORTAL_URL.rstrip("/")


def test_base_url_strips_trailing_slash():
    p = RedoclyPortalProvider(base_url="https://example.com/")
    assert p.base_url == "https://example.com"


def test_http_url_rejected():
    with pytest.raises(ValueError):
        RedoclyPortalProvider(base_url="http://insecure.example.com")

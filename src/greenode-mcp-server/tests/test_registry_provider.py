"""Tests for registry.provider — ProductRef + SpecProvider interface."""
from __future__ import annotations

from greennode.greenode_mcp_server.registry.factory import get_provider
from greennode.greenode_mcp_server.registry.local_dir import LocalDirProvider
from greennode.greenode_mcp_server.registry.provider import (
    ProductRef,
    SpecExtractionError,
    SpecFetchError,
    SpecProvider,
)
from greennode.greenode_mcp_server.registry.redocly_portal import RedoclyPortalProvider


def test_product_ref_defaults_metadata_to_empty_dict():
    ref = ProductRef(name="vks", display_name="VKS API", source_url="https://x/y")
    assert ref.metadata == {}


def test_product_ref_accepts_metadata():
    ref = ProductRef(
        name="vks",
        display_name="VKS API",
        source_url="https://x/y",
        metadata={"etag": "abc"},
    )
    assert ref.metadata == {"etag": "abc"}


def test_spec_fetch_error_carries_product_and_reason():
    err = SpecFetchError("vks", "HTTP 500")
    assert err.product == "vks"
    assert err.reason == "HTTP 500"
    assert "vks" in str(err)
    assert "HTTP 500" in str(err)


def test_spec_extraction_error_carries_product_and_reason():
    err = SpecExtractionError("vlb", "openapi marker not found")
    assert err.product == "vlb"
    assert err.reason == "openapi marker not found"
    assert "vlb" in str(err)


class _DummyProvider:
    async def list_products(self) -> list[ProductRef]:
        return [ProductRef(name="x", display_name="X", source_url="https://x")]

    async def fetch_spec(self, ref: ProductRef) -> dict:
        return {"openapi": "3.0.0", "paths": {}}

    def provider_name(self) -> str:
        return "dummy"


def test_spec_provider_is_a_structural_protocol():
    # Protocol membership check — _DummyProvider structurally matches SpecProvider
    assert isinstance(_DummyProvider(), SpecProvider)


# --- factory ---


def test_factory_returns_redocly_by_default(monkeypatch):
    monkeypatch.delenv("GRN_MCP_SPEC_DIR", raising=False)
    p = get_provider()
    assert isinstance(p, RedoclyPortalProvider)


def test_factory_returns_local_dir_when_env_set(monkeypatch, tmp_path):
    monkeypatch.setenv("GRN_MCP_SPEC_DIR", str(tmp_path))
    p = get_provider()
    assert isinstance(p, LocalDirProvider)
    assert p.directory == tmp_path

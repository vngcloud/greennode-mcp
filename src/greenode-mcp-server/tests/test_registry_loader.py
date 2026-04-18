"""Tests for load_specs — orchestrates provider + cache + CLI flags."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from greennode.greenode_mcp_server.registry.cache import CachedProduct, SpecCache
from greennode.greenode_mcp_server.registry.loader import (
    LoadOptions,
    load_specs,
)
from greennode.greenode_mcp_server.registry.provider import (
    ProductRef,
    SpecFetchError,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_provider(
    refs: list[ProductRef] | None = None,
    fetch_side_effect=None,
) -> MagicMock:
    p = MagicMock()
    p.provider_name.return_value = "fake"
    p.list_products = AsyncMock(return_value=refs or [])
    if fetch_side_effect is None:
        async def default_fetch(ref):
            return {"openapi": "3.0.0", "info": {"title": ref.display_name}, "paths": {}}
        p.fetch_spec = AsyncMock(side_effect=default_fetch)
    else:
        p.fetch_spec = AsyncMock(side_effect=fetch_side_effect)
    return p


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "mcp-specs"


@pytest.fixture
def opts() -> LoadOptions:
    return LoadOptions(refresh=False, offline=False)


# --- happy path ---

@pytest.mark.asyncio
async def test_loads_all_products(cache_dir: Path, opts: LoadOptions):
    refs = [
        ProductRef(name="vks", display_name="VKS", source_url="https://x/vks"),
        ProductRef(name="vlb", display_name="VLB", source_url="https://x/vlb"),
    ]
    provider = _make_provider(refs)
    result = await load_specs(provider, cache_dir, opts)
    assert sorted(s.name for s in result) == ["vks", "vlb"]


@pytest.mark.asyncio
async def test_writes_cache_files(cache_dir: Path, opts: LoadOptions):
    refs = [ProductRef(name="vks", display_name="VKS", source_url="https://x/vks")]
    provider = _make_provider(refs)
    await load_specs(provider, cache_dir, opts)
    assert (cache_dir / "vks.json").exists()
    assert (cache_dir / "_index.json").exists()


# --- cache hit path ---

@pytest.mark.asyncio
async def test_uses_fresh_cache_without_fetching(cache_dir: Path, opts: LoadOptions):
    cache = SpecCache(cache_dir, ttl_seconds=24 * 3600)
    cache.save_spec("vks", {"openapi": "3.0.0", "info": {"title": "Cached VKS"}, "paths": {}})
    cache.save_index(
        [CachedProduct(name="vks", display_name="VKS", source_url="https://x/vks", fetched_at=_now())],
        provider_name="fake",
    )
    refs = [ProductRef(name="vks", display_name="VKS", source_url="https://x/vks")]
    provider = _make_provider(refs)
    result = await load_specs(provider, cache_dir, opts)
    assert len(result) == 1
    provider.fetch_spec.assert_not_called()
    assert result[0].spec["info"]["title"] == "Cached VKS"


# --- refresh flag ---

@pytest.mark.asyncio
async def test_refresh_bypasses_cache(cache_dir: Path):
    cache = SpecCache(cache_dir, ttl_seconds=24 * 3600)
    cache.save_spec("vks", {"openapi": "3.0.0", "info": {"title": "Cached"}, "paths": {}})
    cache.save_index(
        [CachedProduct(name="vks", display_name="VKS", source_url="https://x/vks", fetched_at=_now())],
        provider_name="fake",
    )
    refs = [ProductRef(name="vks", display_name="VKS", source_url="https://x/vks")]
    provider = _make_provider(refs)
    await load_specs(provider, cache_dir, LoadOptions(refresh=True, offline=False))
    provider.fetch_spec.assert_called_once()


# --- offline flag ---

@pytest.mark.asyncio
async def test_offline_uses_cache_only(cache_dir: Path):
    cache = SpecCache(cache_dir, ttl_seconds=24 * 3600)
    cache.save_spec("vks", {"openapi": "3.0.0", "info": {"title": "Cached"}, "paths": {}})
    cache.save_index(
        [CachedProduct(name="vks", display_name="VKS", source_url="https://x/vks", fetched_at=_now())],
        provider_name="fake",
    )
    provider = _make_provider()  # would fail if list_products() called
    result = await load_specs(provider, cache_dir, LoadOptions(refresh=False, offline=True))
    provider.list_products.assert_not_called()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_offline_with_empty_cache_returns_empty_list(cache_dir: Path):
    provider = _make_provider()
    result = await load_specs(provider, cache_dir, LoadOptions(refresh=False, offline=True))
    assert result == []


# --- conflict ---

def test_conflicting_flags_raises():
    with pytest.raises(ValueError):
        LoadOptions(refresh=True, offline=True)


# --- partial failure ---

@pytest.mark.asyncio
async def test_partial_failure_loads_successful_products(cache_dir: Path, opts: LoadOptions):
    refs = [
        ProductRef(name="vks", display_name="VKS", source_url="https://x/vks"),
        ProductRef(name="vlb", display_name="VLB", source_url="https://x/vlb"),
    ]

    async def fetch(ref):
        if ref.name == "vlb":
            raise SpecFetchError("vlb", "HTTP 500")
        return {"openapi": "3.0.0", "info": {"title": ref.display_name}, "paths": {}}

    provider = _make_provider(refs, fetch_side_effect=fetch)
    result = await load_specs(provider, cache_dir, opts)
    assert [s.name for s in result] == ["vks"]


@pytest.mark.asyncio
async def test_partial_failure_uses_stale_cache_when_available(cache_dir: Path, opts: LoadOptions):
    cache = SpecCache(cache_dir, ttl_seconds=0)  # force stale
    cache.save_spec("vlb", {"openapi": "3.0.0", "info": {"title": "Stale VLB"}, "paths": {}})
    cache.save_index(
        [CachedProduct(name="vlb", display_name="VLB", source_url="https://x/vlb", fetched_at=_now())],
        provider_name="fake",
    )
    refs = [ProductRef(name="vlb", display_name="VLB", source_url="https://x/vlb")]

    async def fetch(ref):
        raise SpecFetchError(ref.name, "HTTP 500")

    provider = _make_provider(refs, fetch_side_effect=fetch)
    result = await load_specs(provider, cache_dir, opts)
    assert len(result) == 1
    assert result[0].spec["info"]["title"] == "Stale VLB"


# --- hard failure ---

@pytest.mark.asyncio
async def test_list_products_fails_with_no_cache_raises(cache_dir: Path, opts: LoadOptions):
    provider = MagicMock()
    provider.provider_name.return_value = "fake"
    provider.list_products = AsyncMock(side_effect=SpecFetchError("(landing)", "boom"))
    with pytest.raises(SpecFetchError):
        await load_specs(provider, cache_dir, opts)


@pytest.mark.asyncio
async def test_list_products_fails_falls_back_to_cached_index(cache_dir: Path, opts: LoadOptions):
    cache = SpecCache(cache_dir, ttl_seconds=24 * 3600)
    cache.save_spec("vks", {"openapi": "3.0.0", "info": {"title": "Cached"}, "paths": {}})
    cache.save_index(
        [CachedProduct(name="vks", display_name="VKS", source_url="https://x/vks", fetched_at=_now())],
        provider_name="fake",
    )
    provider = MagicMock()
    provider.provider_name.return_value = "fake"
    provider.list_products = AsyncMock(side_effect=SpecFetchError("(landing)", "boom"))
    result = await load_specs(provider, cache_dir, opts)
    assert len(result) == 1


# --- cacheless providers (LocalDirProvider) ---

@pytest.mark.asyncio
async def test_local_dir_provider_bypasses_cache(cache_dir: Path, opts: LoadOptions):
    """LocalDirProvider must not read or write the production cache."""
    refs = [ProductRef(name="vks", display_name="VKS", source_url="https://x/vks")]
    provider = _make_provider(refs)
    provider.provider_name.return_value = "local-dir"
    await load_specs(provider, cache_dir, opts)
    # No cache files should be written
    assert not cache_dir.exists() or list(cache_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_local_dir_provider_reads_fresh_every_time(cache_dir: Path, opts: LoadOptions):
    """LocalDirProvider must call fetch_spec even if a cache exists."""
    cache = SpecCache(cache_dir, ttl_seconds=24 * 3600)
    cache.save_spec("vks", {"openapi": "3.0.0", "info": {"title": "Old Cached"}, "paths": {}})
    cache.save_index(
        [CachedProduct(name="vks", display_name="VKS", source_url="https://x/vks", fetched_at=_now())],
        provider_name="local-dir",
    )
    refs = [ProductRef(name="vks", display_name="VKS", source_url="https://x/vks")]
    provider = _make_provider(refs)
    provider.provider_name.return_value = "local-dir"
    result = await load_specs(provider, cache_dir, opts)
    provider.fetch_spec.assert_called_once()
    # Result uses fresh provider response, not cached content
    assert result[0].spec["info"]["title"] == "VKS"


# --- cleanup ---

@pytest.mark.asyncio
async def test_cleanup_removes_stale_cache_entries(cache_dir: Path, opts: LoadOptions):
    cache = SpecCache(cache_dir, ttl_seconds=24 * 3600)
    cache.save_spec("old_product", {"openapi": "3.0.0", "paths": {}})
    refs = [ProductRef(name="vks", display_name="VKS", source_url="https://x/vks")]
    provider = _make_provider(refs)
    await load_specs(provider, cache_dir, opts)
    assert not (cache_dir / "old_product.json").exists()
    assert (cache_dir / "vks.json").exists()

"""Tests for SpecCache — on-disk spec store with TTL and metadata."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from greennode.greenode_mcp_server.registry.cache import (
    CachedProduct,
    SpecCache,
)


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "mcp-specs"


@pytest.fixture
def cache(cache_dir: Path) -> SpecCache:
    return SpecCache(cache_dir, ttl_seconds=24 * 3600)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_cache_dir_created_on_demand(cache_dir: Path, cache: SpecCache):
    assert not cache_dir.exists()
    cache.save_spec("vks", {"openapi": "3.0.0", "paths": {}})
    assert cache_dir.exists()
    assert (cache_dir / "vks.json").exists()


def test_load_spec_returns_none_for_missing(cache: SpecCache):
    assert cache.load_spec("nope") is None


def test_save_then_load_roundtrip(cache: SpecCache):
    spec = {"openapi": "3.0.0", "paths": {"/v1/x": {"get": {"summary": "ok"}}}}
    cache.save_spec("vks", spec)
    assert cache.load_spec("vks") == spec


def test_load_index_returns_empty_when_missing(cache: SpecCache):
    assert cache.load_index() == []


def test_save_then_load_index(cache: SpecCache):
    entries = [
        CachedProduct(
            name="vks",
            display_name="VKS API",
            source_url="https://x/y",
            fetched_at=_now_iso(),
            etag='"abc"',
            last_modified="Tue, 15 Apr 2026 08:30:00 GMT",
        )
    ]
    cache.save_index(entries, provider_name="redocly-portal")
    reloaded = cache.load_index()
    assert len(reloaded) == 1
    assert reloaded[0].name == "vks"
    assert reloaded[0].etag == '"abc"'


def test_is_fresh_true_within_ttl(cache: SpecCache):
    entries = [
        CachedProduct(
            name="vks",
            display_name="VKS API",
            source_url="https://x/y",
            fetched_at=_now_iso(),
        )
    ]
    cache.save_index(entries, provider_name="redocly-portal")
    entry = cache.load_index()[0]
    assert cache.is_fresh(entry) is True


def test_is_fresh_false_beyond_ttl(cache_dir: Path):
    short_ttl = SpecCache(cache_dir, ttl_seconds=1)
    entries = [
        CachedProduct(
            name="vks",
            display_name="VKS API",
            source_url="https://x/y",
            fetched_at="2020-01-01T00:00:00+00:00",
        )
    ]
    short_ttl.save_index(entries, provider_name="redocly-portal")
    entry = short_ttl.load_index()[0]
    assert short_ttl.is_fresh(entry) is False


def test_is_fresh_false_when_fetched_at_missing(cache: SpecCache):
    entry = CachedProduct(name="x", display_name="X", source_url="https://x", fetched_at="")
    assert cache.is_fresh(entry) is False


def test_cleanup_removes_unreferenced_specs(cache_dir: Path, cache: SpecCache):
    cache.save_spec("vks", {"openapi": "3.0.0", "paths": {}})
    cache.save_spec("old", {"openapi": "3.0.0", "paths": {}})
    cache.cleanup(keep={"vks"})
    assert (cache_dir / "vks.json").exists()
    assert not (cache_dir / "old.json").exists()


def test_cleanup_keeps_index_file(cache_dir: Path, cache: SpecCache):
    cache.save_index(
        [CachedProduct(name="vks", display_name="VKS API", source_url="https://x/y", fetched_at=_now_iso())],
        provider_name="redocly-portal",
    )
    cache.cleanup(keep={"vks"})
    assert (cache_dir / "_index.json").exists()

"""Orchestrator — combines provider, cache, and runtime flags."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .cache import CachedProduct, SpecCache
from .provider import (
    ProductRef,
    SpecExtractionError,
    SpecFetchError,
    SpecProvider,
)


DEFAULT_TTL_SECONDS = 24 * 3600

logger = logging.getLogger(__name__)


@dataclass
class LoadOptions:
    refresh: bool = False   # bypass cache TTL / conditional GET
    offline: bool = False   # do not touch network

    def __post_init__(self):
        if self.refresh and self.offline:
            raise ValueError(
                "Conflicting flags: --refresh-specs cannot be used with --offline."
            )


@dataclass
class LoadedSpec:
    name: str
    display_name: str
    spec: dict


async def load_specs(
    provider: SpecProvider,
    cache_dir: Path,
    options: LoadOptions,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> list[LoadedSpec]:
    """Load all product specs using `provider`, caching under `cache_dir`."""
    cache = SpecCache(cache_dir, ttl_seconds=ttl_seconds)

    # --- Offline path: only use cache ---
    if options.offline:
        return _load_from_cache_only(cache)

    # --- Fetch product list ---
    refs: list[ProductRef]
    try:
        refs = await provider.list_products()
    except SpecFetchError as e:
        logger.warning("List products failed: %s. Falling back to cached index.", e)
        cached_refs = _cached_refs(cache)
        if not cached_refs:
            raise
        refs = cached_refs

    # --- Per-product load ---
    cached_entries_by_name = {e.name: e for e in cache.load_index()}
    loaded: list[LoadedSpec] = []
    fresh_index: list[CachedProduct] = []

    for ref in refs:
        cached_entry = cached_entries_by_name.get(ref.name)
        if cached_entry and cached_entry.etag:
            ref.metadata.setdefault("etag", cached_entry.etag)
        if cached_entry and cached_entry.last_modified:
            ref.metadata.setdefault("last_modified", cached_entry.last_modified)

        use_cache = (
            not options.refresh
            and cached_entry is not None
            and cache.is_fresh(cached_entry)
            and cache.load_spec(ref.name) is not None
        )

        if use_cache:
            spec = cache.load_spec(ref.name)
            assert spec is not None
            loaded.append(LoadedSpec(ref.name, ref.display_name, spec))
            fresh_index.append(cached_entry)
            continue

        try:
            spec = await provider.fetch_spec(ref)
        except (SpecFetchError, SpecExtractionError) as e:
            logger.warning(
                "Failed to fetch spec for %r: %s. %s",
                ref.name,
                e,
                "Using cached copy." if cached_entry and cache.load_spec(ref.name) else "Skipping.",
            )
            if cached_entry and (stale_spec := cache.load_spec(ref.name)) is not None:
                loaded.append(LoadedSpec(ref.name, ref.display_name, stale_spec))
                fresh_index.append(cached_entry)
            continue

        cache.save_spec(ref.name, spec)
        fresh_index.append(CachedProduct(
            name=ref.name,
            display_name=ref.display_name,
            source_url=ref.source_url,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            etag=ref.metadata.get("etag"),
            last_modified=ref.metadata.get("last_modified"),
        ))
        loaded.append(LoadedSpec(ref.name, ref.display_name, spec))

    cache.save_index(fresh_index, provider_name=provider.provider_name())
    cache.cleanup(keep={e.name for e in fresh_index})

    return loaded


def _cached_refs(cache: SpecCache) -> list[ProductRef]:
    return [
        ProductRef(
            name=e.name,
            display_name=e.display_name,
            source_url=e.source_url,
            metadata={
                "etag": e.etag or "",
                "last_modified": e.last_modified or "",
            },
        )
        for e in cache.load_index()
    ]


def _load_from_cache_only(cache: SpecCache) -> list[LoadedSpec]:
    loaded: list[LoadedSpec] = []
    for entry in cache.load_index():
        spec = cache.load_spec(entry.name)
        if spec is None:
            continue
        loaded.append(LoadedSpec(entry.name, entry.display_name, spec))
    return loaded

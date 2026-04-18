"""On-disk cache for OpenAPI specs and provider metadata."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


INDEX_FILE = "_index.json"
INDEX_SCHEMA_VERSION = "1.0"


@dataclass
class CachedProduct:
    """Per-product metadata stored in the cache index."""

    name: str
    display_name: str
    source_url: str
    fetched_at: str                    # ISO-8601 UTC; empty string = unknown
    etag: str | None = None
    last_modified: str | None = None
    provider_metadata: dict = field(default_factory=dict)


class SpecCache:
    """JSON file cache under ~/.greenode/mcp-specs/."""

    def __init__(self, cache_dir: Path, ttl_seconds: int) -> None:
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = ttl_seconds

    # --- Spec file I/O ---

    def spec_path(self, product: str) -> Path:
        return self.cache_dir / f"{product}.json"

    def load_spec(self, product: str) -> dict | None:
        path = self.spec_path(product)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_spec(self, product: str, spec: dict) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.spec_path(product).write_text(
            json.dumps(spec, ensure_ascii=False),
            encoding="utf-8",
        )

    # --- Index file I/O ---

    def _index_path(self) -> Path:
        return self.cache_dir / INDEX_FILE

    def load_index(self) -> list[CachedProduct]:
        path = self._index_path()
        if not path.exists():
            return []
        try:
            blob = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        entries = []
        for item in blob.get("products", []):
            entries.append(CachedProduct(
                name=item.get("name", ""),
                display_name=item.get("display_name", ""),
                source_url=item.get("source_url", ""),
                fetched_at=item.get("fetched_at", ""),
                etag=item.get("etag"),
                last_modified=item.get("last_modified"),
                provider_metadata=item.get("provider_metadata", {}),
            ))
        return entries

    def save_index(self, entries: list[CachedProduct], provider_name: str) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": INDEX_SCHEMA_VERSION,
            "provider": provider_name,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "products": [asdict(e) for e in entries],
        }
        self._index_path().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --- Freshness + cleanup ---

    def is_fresh(self, entry: CachedProduct) -> bool:
        if not entry.fetched_at:
            return False
        try:
            fetched = datetime.fromisoformat(entry.fetched_at)
        except ValueError:
            return False
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        return age < self.ttl_seconds

    def cleanup(self, keep: set[str]) -> None:
        """Delete cached spec files not in `keep`. Always preserves _index.json."""
        if not self.cache_dir.exists():
            return
        for f in self.cache_dir.iterdir():
            if not f.is_file():
                continue
            if f.name == INDEX_FILE:
                continue
            if f.suffix != ".json":
                continue
            product = f.stem
            if product not in keep:
                try:
                    f.unlink()
                except OSError:
                    pass

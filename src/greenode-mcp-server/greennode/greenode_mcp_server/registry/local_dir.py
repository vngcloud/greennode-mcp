"""Local directory provider — reads specs from disk. For dev and tests."""
from __future__ import annotations

import json
from pathlib import Path

from .provider import ProductRef, SpecFetchError


class LocalDirProvider:
    """Lists and loads OpenAPI specs from a local directory of *.json files.

    Intended for unit tests and air-gapped dev loops. Activated by the
    GRN_MCP_SPEC_DIR env var in registry.factory.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    async def list_products(self) -> list[ProductRef]:
        refs: list[ProductRef] = []
        if not self.directory.exists():
            return refs
        for path in sorted(self.directory.glob("*.json")):
            if path.name.startswith("_"):
                continue  # Skip _index.json, _meta.json, etc.
            try:
                spec = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            display_name = spec.get("info", {}).get("title") or path.stem.upper()
            refs.append(ProductRef(
                name=path.stem,
                display_name=display_name,
                source_url=str(path),
            ))
        return refs

    async def fetch_spec(self, ref: ProductRef) -> dict:
        path = Path(ref.source_url)
        if not path.exists():
            raise SpecFetchError(ref.name, f"file not found: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise SpecFetchError(ref.name, str(e)) from e

    def provider_name(self) -> str:
        return "local-dir"

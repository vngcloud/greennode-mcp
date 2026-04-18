"""OpenAPI endpoint index built from specs loaded by the registry layer."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from .registry.factory import get_provider
from .registry.loader import LoadOptions, load_specs


DEFAULT_CACHE_DIR = Path.home() / ".greenode" / "mcp-specs"


@dataclass
class EndpointEntry:
    product: str
    method: str
    path: str
    summary: str
    description: str
    parameters: list = field(default_factory=list)
    request_body: dict | None = None
    servers: dict = field(default_factory=dict)

    def format(self) -> str:
        lines = [f"{self.method} {self.path} — {self.summary}"]
        if self.parameters:
            param_names = [
                p.get("name", "") for p in self.parameters
                if p.get("in") in ("query", "path") and p.get("name")
            ]
            if param_names:
                lines.append(f"  Params: {', '.join(param_names)}")
        if self.request_body:
            schema = (
                self.request_body
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            required = schema.get("required", [])
            props = list(schema.get("properties", {}).keys())[:8]
            if props:
                parts = [f"{p} (required)" if p in required else p for p in props[:6]]
                lines.append(f"  Body: {{ {', '.join(parts)} }}")
        return "\n".join(lines)


def _parse_servers(spec: dict) -> dict:
    servers: dict[str, str] = {}
    for s in spec.get("servers", []):
        url = s.get("url", "").rstrip("/")
        if not url:
            continue
        url_lower = url.lower()
        desc_lower = s.get("description", "").lower()
        if "hcm" in url_lower or "hcm" in desc_lower:
            servers["HCM-3"] = url
        elif "han" in url_lower or "han" in desc_lower:
            servers["HAN"] = url
        else:
            servers.setdefault("HCM-3", url)
            servers.setdefault("HAN", url)
    return servers


def _build_entries(product: str, spec: dict) -> list[EndpointEntry]:
    entries: list[EndpointEntry] = []
    servers = _parse_servers(spec)
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"):
                continue
            if not isinstance(op, dict):
                continue
            entries.append(EndpointEntry(
                product=product,
                method=method.upper(),
                path=path,
                summary=op.get("summary", ""),
                description=op.get("description", ""),
                parameters=op.get("parameters", []),
                request_body=op.get("requestBody"),
                servers=servers,
            ))
    return entries


_INDEX: list[EndpointEntry] | None = None


def initialize_index(
    refresh: bool = False,
    offline: bool = False,
    cache_dir: Path | None = None,
) -> list[EndpointEntry]:
    """Load specs via the registry and build the in-memory endpoint index."""
    global _INDEX
    provider = get_provider()
    options = LoadOptions(refresh=refresh, offline=offline)
    loaded = asyncio.run(load_specs(provider, cache_dir or DEFAULT_CACHE_DIR, options))
    entries: list[EndpointEntry] = []
    for s in loaded:
        entries.extend(_build_entries(s.name, s.spec))
    _INDEX = entries
    return entries


def set_index(entries: list[EndpointEntry]) -> None:
    """Replace the singleton index (for tests)."""
    global _INDEX
    _INDEX = list(entries)


def get_index() -> list[EndpointEntry]:
    """Return the singleton endpoint index. Raise if not initialized."""
    global _INDEX
    if _INDEX is None:
        raise RuntimeError(
            "api_index not initialized. Call initialize_index() at server startup."
        )
    return _INDEX


def reset_index() -> None:
    """Reset the singleton index. Used in tests."""
    global _INDEX
    _INDEX = None


def search(query: str, product: str | None = None, max_results: int = 5) -> list[EndpointEntry]:
    terms = [t.lower() for t in query.split() if t]
    if not terms:
        return []
    results = []
    for entry in get_index():
        if product and entry.product != product:
            continue
        searchable = f"{entry.product} {entry.method} {entry.path} {entry.summary} {entry.description}".lower()
        if all(term in searchable for term in terms):
            results.append(entry)
    return results[:max_results]

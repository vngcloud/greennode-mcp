"""OpenAPI spec loader and endpoint index for VNG Cloud APIs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SPECS_DIR = Path(__file__).parent.parent.parent / "specs"


@dataclass
class EndpointEntry:
    """A single API endpoint extracted from an OpenAPI spec."""

    product: str
    method: str
    path: str
    summary: str
    description: str
    parameters: list = field(default_factory=list)
    request_body: dict | None = None
    servers: dict = field(default_factory=dict)  # {"HCM-3": "https://...", "HAN": "https://..."}

    def format(self) -> str:
        """Format entry for search_api tool output."""
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
    """Extract region → base URL mapping from OpenAPI servers[]."""
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
            # Single server (no region hint) — use for all regions
            servers.setdefault("HCM-3", url)
            servers.setdefault("HAN", url)
    return servers


def load_index() -> list[EndpointEntry]:
    """Load all OpenAPI specs from SPECS_DIR and return a flat endpoint list."""
    entries: list[EndpointEntry] = []
    if not SPECS_DIR.exists():
        return entries

    for spec_file in sorted(SPECS_DIR.glob("*.json")):
        product = spec_file.stem
        try:
            spec = json.loads(spec_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

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


def get_index() -> list[EndpointEntry]:
    """Return the singleton endpoint index, loading specs on first call."""
    global _INDEX
    if _INDEX is None:
        _INDEX = load_index()
    return _INDEX


def reset_index() -> None:
    """Reset the singleton index. Used in tests."""
    global _INDEX
    _INDEX = None


def search(query: str, product: str | None = None, max_results: int = 5) -> list[EndpointEntry]:
    """Keyword search over the endpoint index.

    All whitespace-separated terms must appear in the searchable text (AND logic).
    Returns up to max_results entries.
    """
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

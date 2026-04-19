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
        lines = [f"[{self.product}] {self.method} {self.path} — {self.summary}"]
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


def _stem(term: str) -> str:
    """Simple singular form: trim trailing 's' for words longer than 4 chars."""
    if len(term) > 4 and term.endswith("s"):
        return term[:-1]
    return term


# Cloud terminology varies. VNG Cloud specs use names that differ from
# user habits (AWS/GCP-influenced). Keep this list small and concrete —
# only proven sources of query failure, not speculative coverage.
SYNONYMS: dict[str, list[str]] = {
    "vpc": ["network"],             # VNG Cloud calls VPC "Network"
    "instance": ["server"],         # VNG Cloud calls instance "Server"
    "firewall": ["secgroup", "security"],
    "pvc": ["persistentvolumeclaim"],
    "k8s": ["kubernetes"],
    "lb": ["loadbalancer"],
    "loadbalancer": ["lb"],
}


def _term_variants(term: str) -> list[str]:
    """All acceptable substitutes for this term: term + stem + synonyms."""
    out = [term]
    stem = _stem(term)
    if stem != term:
        out.append(stem)
    for syn in SYNONYMS.get(term, []):
        out.append(syn)
        syn_stem = _stem(syn)
        if syn_stem != syn:
            out.append(syn_stem)
    return out


def _term_matches(hay: str, term: str) -> bool:
    """True if any variant of `term` appears in `hay`."""
    return any(v in hay for v in _term_variants(term))


def _score(entry: EndpointEntry, terms: list[str]) -> int:
    """Relevance score — summary > path > description > product."""
    score = 0
    summary = entry.summary.lower()
    path = entry.path.lower()
    desc = entry.description.lower()
    prod = entry.product.lower()
    for term in terms:
        variants = _term_variants(term)
        if any(v in summary for v in variants):
            score += 3
        if any(v in path for v in variants):
            score += 2
        if any(v in desc for v in variants):
            score += 1
        if any(v in prod for v in variants):
            score += 1
    return score


def _filter(entries: list[EndpointEntry], terms: list[str], require_all: bool) -> list[EndpointEntry]:
    matched: list[EndpointEntry] = []
    for e in entries:
        hay = f"{e.product} {e.method} {e.path} {e.summary} {e.description}".lower()
        if require_all:
            if all(_term_matches(hay, t) for t in terms):
                matched.append(e)
        else:
            if any(_term_matches(hay, t) for t in terms):
                matched.append(e)
    return matched


def search(query: str, product: str | None = None, max_results: int = 5) -> list[EndpointEntry]:
    """Keyword search with smart fallback when strict match returns nothing.

    Tier 1: AND all terms, filtered by product (most precise)
    Tier 2: AND all terms, all products (if product filter excluded matches)
    Tier 3: OR any term, filtered by product
    Tier 4: OR any term, all products

    Results ranked by relevance (summary > path > description).
    """
    terms = [t.lower() for t in query.split() if t]
    if not terms:
        return []

    all_entries = get_index()
    scoped = [e for e in all_entries if not product or e.product == product]

    results: list[EndpointEntry] = []
    for tier_entries, require_all in (
        (scoped, True),
        (all_entries if product else scoped, True),
        (scoped, False),
        (all_entries if product else scoped, False),
    ):
        results = _filter(tier_entries, terms, require_all=require_all)
        if results:
            break

    results.sort(key=lambda e: _score(e, terms), reverse=True)
    return results[:max_results]

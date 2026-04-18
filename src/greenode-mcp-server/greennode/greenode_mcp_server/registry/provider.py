"""Provider abstraction — different spec sources implement this interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ProductRef:
    """Opaque identifier for a product and its spec location.

    `metadata` is provider-specific (HTTP ETag, S3 version, OCI digest, etc.).
    """

    name: str
    display_name: str
    source_url: str
    metadata: dict = field(default_factory=dict)


class SpecFetchError(Exception):
    """Raised when a provider cannot retrieve a spec (network, HTTP error)."""

    def __init__(self, product: str, reason: str) -> None:
        super().__init__(f"Failed to fetch spec for {product!r}: {reason}")
        self.product = product
        self.reason = reason


class SpecExtractionError(Exception):
    """Raised when a provider cannot parse a fetched response into an OpenAPI spec."""

    def __init__(self, product: str, reason: str) -> None:
        super().__init__(f"Failed to extract spec for {product!r}: {reason}")
        self.product = product
        self.reason = reason


@runtime_checkable
class SpecProvider(Protocol):
    """A source of OpenAPI specs.

    Implementations must be safe to instantiate at startup and cheap to call
    repeatedly (one `list_products()` call, then one `fetch_spec()` per product).
    """

    async def list_products(self) -> list[ProductRef]: ...

    async def fetch_spec(self, ref: ProductRef) -> dict: ...

    def provider_name(self) -> str: ...

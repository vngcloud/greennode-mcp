"""Identity-scoped TTL cache for static Agentbase reference lookups."""

from __future__ import annotations

from greennode.mcp_core.cache import DEFAULT_MAXSIZE
from greennode.mcp_core.cache import DiscoveryCache as _CoreDiscoveryCache
from greennode.mcp_core.http import current_identity


# Only static reference data is cached (never per-caller mutable resources).
TTL_CONFIG: dict[str, int] = {
    "list_condition_operators": 300,  # supported operators change rarely
}


class DiscoveryCache(_CoreDiscoveryCache):
    """Agentbase cache: core cache with this package's TTLs + caller-identity keys.

    Every key is prefixed with current_identity() (hash of the caller token, or
    'service'), so under passthrough one caller's cached result is never served
    to another.
    """

    def __init__(
        self, ttl_config: dict[str, int] | None = None, maxsize: int = DEFAULT_MAXSIZE, timer=None
    ):
        super().__init__(
            ttl_config if ttl_config is not None else TTL_CONFIG, maxsize=maxsize, timer=timer
        )

    async def get_or_fetch(self, tool, key, fetch, refresh=False):
        """Cache lookup with the caller identity baked into the key."""
        scoped_key = (current_identity(), key)
        return await super().get_or_fetch(tool, scoped_key, fetch, refresh)

"""Env-driven, passthrough-only configuration for the Agentbase MCP server.

Unlike the product-template config, this server holds NO service-account
credentials and does NOT read ~/.greennode: every upstream call forwards the
caller's inbound bearer token (see middleware.py / server.py). Region is a
single prod region. All six Agentbase service base URLs are baked in up front
so adding later services needs no config change.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal


Region = Literal["prod"]

# All six Agentbase services, ported service-by-service after this pilot.
SERVICES: tuple[str, ...] = ("policy", "cr", "gateway", "identity", "memory", "runtime")

# Prod-only base URLs (the Agentbase API is single-region; mirrors the source
# server's prod-only design). Overridable per-service via AGENTBASE_<SERVICE>_BASE_URL.
BASE_URLS: dict[str, str] = {
    "policy": "https://agentbase.api.vngcloud.vn/policy",
    "cr": "https://agentbase.api.vngcloud.vn/cr",
    "gateway": "https://agentbase.api.vngcloud.vn/gateway",
    "identity": "https://agentbase.api.vngcloud.vn/identity",
    "memory": "https://agentbase.api.vngcloud.vn/memory",
    "runtime": "https://agentbase.api.vngcloud.vn/runtime",
}

_ENV_NAME = "AGENTBASE_DEFAULT_REGION"


@dataclass
class AgentbaseConfig:
    """Top-level Agentbase configuration (no credentials — passthrough only)."""

    default_region: str
    base_urls: dict[str, str]

    def get_base_url(self, region: str | None, service: str) -> str:
        """Return the base URL for *service* (region ignored — single prod region).

        Required by ``mcp_core.http.BaseClient`` (the ``_HasBaseUrls`` protocol).
        """
        try:
            return self.base_urls[service]
        except KeyError:
            raise ValueError(
                f"Service '{service}' is not configured. Known services: {list(self.base_urls)}"
            ) from None


def load_config(env: Mapping[str, str] | None = None) -> AgentbaseConfig:
    """Load config from environment overrides (no files, no credentials).

    Env vars (all optional):
    - AGENTBASE_DEFAULT_REGION: region label (default "prod").
    - AGENTBASE_<SERVICE>_BASE_URL: override one service's base URL
      (e.g. AGENTBASE_POLICY_BASE_URL).
    """
    e = env if env is not None else os.environ
    base_urls = dict(BASE_URLS)
    for service in SERVICES:
        override = e.get(f"AGENTBASE_{service.upper()}_BASE_URL")
        if override:
            base_urls[service] = override
    return AgentbaseConfig(default_region=e.get(_ENV_NAME, "prod"), base_urls=base_urls)

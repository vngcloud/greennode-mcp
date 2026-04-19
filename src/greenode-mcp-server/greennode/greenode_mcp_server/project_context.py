"""Auto-fetch and cache the user's VNG Cloud project_id.

VNG Cloud APIs that embed `{projectId}` in the URL path need the caller's
project UUID. Every call looks up the same value from `/v1/projects`, so
we fetch once on first use and cache in memory. `call_api` substitutes
the placeholder transparently.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from greennode.greenode_mcp_server.auth import TokenManager
from greennode.greenode_mcp_server.config import VksConfig


logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 10.0
PROJECTS_PATH = "/v1/projects"


class ProjectContext:
    """Lazily fetches and caches the user's first project_id.

    Thread-safe under asyncio via an internal lock — concurrent callers
    that arrive before the first fetch completes will share the same
    in-flight request.
    """

    def __init__(self, config: VksConfig, token_manager: TokenManager) -> None:
        self._config = config
        self._token_manager = token_manager
        self._project_id: str | None = None
        self._lock = asyncio.Lock()

    def cached_project_id(self) -> str | None:
        """Return the cached project_id, or None if never fetched."""
        return self._project_id

    async def get_project_id(self, region: str | None = None) -> str:
        """Return the project_id, fetching from vServer on first call."""
        async with self._lock:
            if self._project_id:
                return self._project_id

            endpoints = self._config.get_endpoints(region)
            url = f"{endpoints.vserver.rstrip('/')}{PROJECTS_PATH}"
            token = await self._token_manager.get_token()

            try:
                async with httpx.AsyncClient(timeout=FETCH_TIMEOUT) as client:
                    resp = await client.get(
                        url,
                        headers={"Authorization": f"Bearer {token}"},
                    )
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Failed to fetch project_id: {exc}") from exc

            if resp.status_code != 200:
                raise RuntimeError(
                    f"Failed to fetch project_id from {url}: HTTP {resp.status_code}"
                )

            data = resp.json()
            projects = data.get("projects") or []
            if not projects:
                raise RuntimeError(
                    "Account has no projects. Create one via the VNG Cloud console first."
                )
            if len(projects) > 1:
                logger.warning(
                    "Account has %d projects. Using first (%s).",
                    len(projects),
                    projects[0].get("projectId"),
                )

            project_id = projects[0].get("projectId")
            if not project_id:
                raise RuntimeError(
                    f"vServer /v1/projects response missing projectId field: {projects[0]}"
                )
            self._project_id = project_id
            logger.info("Loaded project_id: %s", project_id)
            return project_id

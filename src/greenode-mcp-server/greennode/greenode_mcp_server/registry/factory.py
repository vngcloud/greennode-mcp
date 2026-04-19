"""Factory selecting the active spec provider. Change here to migrate sources."""
from __future__ import annotations

import os
from pathlib import Path

from .local_dir import LocalDirProvider
from .provider import SpecProvider
from .redocly_portal import RedoclyPortalProvider


SPEC_DIR_ENV = "GRN_MCP_SPEC_DIR"


def get_provider() -> SpecProvider:
    """Return the active spec provider.

    - If GRN_MCP_SPEC_DIR is set, use LocalDirProvider (for dev/test/air-gapped).
    - Otherwise use RedoclyPortalProvider (default for all end users).

    When migrating to a different source, change the default return here.
    """
    spec_dir = os.environ.get(SPEC_DIR_ENV)
    if spec_dir:
        return LocalDirProvider(Path(spec_dir))
    return RedoclyPortalProvider()

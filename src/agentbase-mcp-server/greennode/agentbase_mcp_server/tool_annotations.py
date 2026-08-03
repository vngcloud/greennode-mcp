"""Shared ToolAnnotations constants (effect, not name — mirrors vks)."""

from __future__ import annotations

from mcp.types import ToolAnnotations


READ = ToolAnnotations(readOnlyHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True)

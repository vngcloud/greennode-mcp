"""Opt-in diagnostic helpers to summarize an inbound request's auth surface.

DIAGNOSTIC ONLY. Never verifies JWT signatures and never includes the full
bearer token (only a short prefix + length). Used by the --auth-debug flag to
measure what an upstream (e.g. the MCP Gateway) actually sends downstream.
"""

from __future__ import annotations

from typing import Mapping


_TOKEN_PREFIX_LEN = 6


def _redact_token(token: str) -> dict:
    """Return non-reversible token metadata only (never the full token)."""
    return {
        "token_present": True,
        "token_len": len(token),
        "token_prefix": token[:_TOKEN_PREFIX_LEN],
    }


def summarize_request(method: str, path: str, headers: Mapping[str, str]) -> dict:
    """Build a safe, JSON-serializable summary of a request's auth surface.

    Never raises and never includes the full bearer token.
    """
    summary: dict = {"method": method, "path": path}
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    summary["has_authorization"] = bool(auth)
    if not auth:
        summary["auth_scheme"] = None
        summary["forwarding_headers"] = {}
        return summary
    parts = auth.split(" ", 1)
    summary["auth_scheme"] = parts[0]
    token = parts[1].strip() if len(parts) == 2 else ""
    if token:
        summary.update(_redact_token(token))
    summary["forwarding_headers"] = {}
    return summary

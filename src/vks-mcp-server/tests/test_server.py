"""Tests for server CLI arg parsing and BearerTokenMiddleware."""
from __future__ import annotations

import argparse

import pytest

from greennode.vks_mcp_server.server import _build_parser


def _parse_args(argv: list[str]) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def test_default_transport_is_stdio():
    args = _parse_args([])
    assert args.transport == "stdio"


def test_transport_http_flag():
    args = _parse_args(["--transport", "streamable-http"])
    assert args.transport == "streamable-http"


def test_default_host_and_port():
    args = _parse_args(["--transport", "streamable-http"])
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_custom_host_and_port():
    args = _parse_args(["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9000"])
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_api_key_default_is_none():
    args = _parse_args([])
    assert args.api_key is None


def test_api_key_flag():
    args = _parse_args(["--api-key", "mysecrettoken"])
    assert args.api_key == "mysecrettoken"


def test_invalid_transport_raises():
    with pytest.raises(SystemExit):
        _parse_args(["--transport", "sse"])

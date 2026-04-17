"""Tests for api_index — spec loader and endpoint search."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from greennode.greenode_mcp_server.api_index import (
    EndpointEntry,
    _parse_servers,
    load_index,
    reset_index,
    search,
)

MINIMAL_SPEC = {
    "servers": [{"url": "https://hcm-3.api.vngcloud.vn/vks"}],
    "paths": {
        "/v1/clusters": {
            "get": {
                "summary": "List all clusters",
                "description": "Returns all clusters for the account",
                "parameters": [{"name": "page", "in": "query"}],
            },
            "post": {
                "summary": "Create a cluster",
                "description": "Creates a new VKS cluster",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "required": ["name", "version"],
                                "properties": {
                                    "name": {},
                                    "version": {},
                                    "region": {},
                                },
                            }
                        }
                    }
                },
            },
        },
        "/v1/clusters/{cluster_id}": {
            "get": {"summary": "Get cluster details", "description": ""},
            "delete": {"summary": "Delete a cluster", "description": ""},
        },
    },
}


@pytest.fixture(autouse=True)
def _reset(monkeypatch, tmp_path):
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    monkeypatch.setattr("greennode.greenode_mcp_server.api_index.SPECS_DIR", specs_dir)
    reset_index()
    yield
    reset_index()


def _write_spec(specs_dir: Path, name: str, spec: dict) -> None:
    (specs_dir / f"{name}.json").write_text(json.dumps(spec))


def _get_specs_dir(monkeypatch_fixture) -> Path:
    import greennode.greenode_mcp_server.api_index as m
    return m.SPECS_DIR


# --- load_index ---

def test_load_index_builds_entries(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    entries = load_index()
    assert len(entries) == 4
    methods = {e.method for e in entries}
    assert methods == {"GET", "POST", "DELETE"}


def test_load_index_sets_product_from_filename(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vlb", MINIMAL_SPEC)
    entries = load_index()
    assert all(e.product == "vlb" for e in entries)


def test_load_index_empty_dir_returns_empty():
    entries = load_index()
    assert entries == []


def test_load_index_invalid_json_skipped(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    (m.SPECS_DIR / "bad.json").write_text("not json {{{")
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    entries = load_index()
    assert len(entries) == 4  # bad.json skipped


def test_load_index_skips_non_http_methods(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    spec = {
        "paths": {
            "/v1/test": {
                "get": {"summary": "ok", "description": ""},
                "options": {"summary": "options", "description": ""},
                "x-custom": {"summary": "custom", "description": ""},
            }
        }
    }
    _write_spec(m.SPECS_DIR, "test", spec)
    entries = load_index()
    assert len(entries) == 1
    assert entries[0].method == "GET"


# --- search ---

def test_search_by_summary_keyword(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    results = search("list clusters")
    assert len(results) >= 1
    assert results[0].path == "/v1/clusters"
    assert results[0].method == "GET"


def test_search_by_path_keyword(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    results = search("clusters")
    assert len(results) >= 1


def test_search_by_product_name(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    results = search("vks")
    assert len(results) >= 1
    assert all(e.product == "vks" for e in results)


def test_search_filters_by_product(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    _write_spec(m.SPECS_DIR, "vlb", {
        "paths": {
            "/v2/loadbalancers": {
                "get": {"summary": "List load balancers", "description": ""},
            }
        }
    })
    results = search("list", product="vlb")
    assert all(e.product == "vlb" for e in results)


def test_search_returns_empty_for_no_match(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    assert search("xyz_nonexistent_endpoint_query") == []


def test_search_respects_max_results(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    results = search("cluster", max_results=2)
    assert len(results) <= 2


def test_search_empty_query_returns_empty(tmp_path, monkeypatch):
    import greennode.greenode_mcp_server.api_index as m
    _write_spec(m.SPECS_DIR, "vks", MINIMAL_SPEC)
    assert search("") == []


# --- _parse_servers ---

def test_parse_servers_hcm():
    servers = _parse_servers({"servers": [{"url": "https://hcm-3.api.vngcloud.vn/vks"}]})
    assert servers.get("HCM-3") == "https://hcm-3.api.vngcloud.vn/vks"


def test_parse_servers_han():
    servers = _parse_servers({"servers": [{"url": "https://han-1.api.vngcloud.vn/vks"}]})
    assert servers.get("HAN") == "https://han-1.api.vngcloud.vn/vks"


def test_parse_servers_single_server_maps_to_both_regions():
    servers = _parse_servers({"servers": [{"url": "https://vks.api.vngcloud.vn"}]})
    assert "HCM-3" in servers
    assert "HAN" in servers


def test_parse_servers_empty():
    assert _parse_servers({}) == {}


# --- EndpointEntry.format ---

def test_endpoint_entry_format_includes_method_and_path():
    entry = EndpointEntry(
        product="vks", method="GET", path="/v1/clusters",
        summary="List all clusters", description="",
    )
    result = entry.format()
    assert "GET" in result
    assert "/v1/clusters" in result
    assert "List all clusters" in result

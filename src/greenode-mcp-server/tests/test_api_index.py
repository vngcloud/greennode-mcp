"""Tests for api_index — endpoint search over the in-memory index."""
from __future__ import annotations

import pytest

from greennode.greenode_mcp_server.api_index import (
    EndpointEntry,
    _parse_servers,
    _build_entries,
    get_index,
    reset_index,
    search,
    set_index,
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
                                "properties": {"name": {}, "version": {}, "region": {}},
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
def _reset_index_fixture():
    reset_index()
    yield
    reset_index()


def _setup(entries):
    set_index(entries)


# --- _build_entries ---

def test_build_entries_count():
    entries = _build_entries("vks", MINIMAL_SPEC)
    assert len(entries) == 4


def test_build_entries_methods():
    entries = _build_entries("vks", MINIMAL_SPEC)
    assert {e.method for e in entries} == {"GET", "POST", "DELETE"}


def test_build_entries_skips_non_http_methods():
    spec = {"paths": {"/v1/x": {
        "get": {"summary": "ok", "description": ""},
        "options": {"summary": "opts", "description": ""},
        "x-custom": {"summary": "cust", "description": ""},
    }}}
    entries = _build_entries("x", spec)
    assert len(entries) == 1


def test_build_entries_product_name():
    entries = _build_entries("vlb", MINIMAL_SPEC)
    assert all(e.product == "vlb" for e in entries)


# --- get_index / set_index / reset_index ---

def test_get_index_raises_before_initialization():
    with pytest.raises(RuntimeError):
        get_index()


def test_set_and_get_index():
    entry = EndpointEntry(product="vks", method="GET", path="/v1/x", summary="x", description="")
    set_index([entry])
    assert get_index() == [entry]


# --- search ---

def test_search_by_summary_keyword():
    _setup(_build_entries("vks", MINIMAL_SPEC))
    results = search("list clusters")
    assert len(results) >= 1
    assert results[0].path == "/v1/clusters"
    assert results[0].method == "GET"


def test_search_by_path_keyword():
    _setup(_build_entries("vks", MINIMAL_SPEC))
    assert len(search("clusters")) >= 1


def test_search_by_product_name():
    _setup(_build_entries("vks", MINIMAL_SPEC))
    results = search("vks")
    assert len(results) >= 1
    assert all(e.product == "vks" for e in results)


def test_search_filters_by_product():
    entries = _build_entries("vks", MINIMAL_SPEC) + _build_entries("vlb", {
        "paths": {"/v2/lbs": {"get": {"summary": "List load balancers", "description": ""}}}
    })
    _setup(entries)
    results = search("list", product="vlb")
    assert all(e.product == "vlb" for e in results)


def test_search_returns_empty_for_no_match():
    _setup(_build_entries("vks", MINIMAL_SPEC))
    assert search("xyz_nonexistent") == []


def test_search_respects_max_results():
    _setup(_build_entries("vks", MINIMAL_SPEC))
    assert len(search("cluster", max_results=2)) <= 2


def test_search_empty_query_returns_empty():
    _setup(_build_entries("vks", MINIMAL_SPEC))
    assert search("") == []


# --- _parse_servers ---

def test_parse_servers_hcm():
    s = _parse_servers({"servers": [{"url": "https://hcm-3.api.vngcloud.vn/vks"}]})
    assert s.get("HCM-3") == "https://hcm-3.api.vngcloud.vn/vks"


def test_parse_servers_han():
    s = _parse_servers({"servers": [{"url": "https://han-1.api.vngcloud.vn/vks"}]})
    assert s.get("HAN") == "https://han-1.api.vngcloud.vn/vks"


def test_parse_servers_single_server_maps_to_both_regions():
    s = _parse_servers({"servers": [{"url": "https://vks.api.vngcloud.vn"}]})
    assert "HCM-3" in s and "HAN" in s


def test_parse_servers_empty():
    assert _parse_servers({}) == {}


# --- EndpointEntry.format ---

def test_endpoint_entry_format_includes_method_and_path():
    e = EndpointEntry(product="vks", method="GET", path="/v1/clusters",
                      summary="List all clusters", description="")
    result = e.format()
    assert "GET" in result
    assert "/v1/clusters" in result
    assert "List all clusters" in result


def test_endpoint_entry_format_includes_product_prefix():
    e = EndpointEntry(product="vlb", method="GET", path="/v2/lbs",
                      summary="List LBs", description="")
    assert "[vlb]" in e.format()


# --- Fallback and stemming ---

def test_search_falls_back_to_all_products_when_scoped_empty():
    """Query for 'flavor' in vks (no flavor there) should fall back to vserver."""
    entries = _build_entries("vks", MINIMAL_SPEC) + _build_entries("vserver", {
        "paths": {"/v1/flavors": {"get": {"summary": "List flavors", "description": ""}}}
    })
    _setup(entries)
    results = search("flavor", product="vks")
    assert len(results) >= 1
    assert results[0].product == "vserver"


def test_search_stemming_matches_plural():
    """Query 'clusters' (plural) matches entries with 'cluster' (singular)."""
    spec = {"paths": {"/v1/x": {"get": {"summary": "Get cluster details", "description": ""}}}}
    _setup(_build_entries("vks", spec))
    assert len(search("clusters")) >= 1


def test_search_stemming_matches_stem_to_plural():
    """Query 'cluster' matches entries with 'clusters' (substring match)."""
    spec = {"paths": {"/v1/x": {"get": {"summary": "List clusters", "description": ""}}}}
    _setup(_build_entries("vks", spec))
    assert len(search("cluster")) >= 1


def test_search_or_fallback_when_and_fails():
    """Multi-term query where no entry has both terms falls back to OR."""
    entries = [
        EndpointEntry(product="vks", method="GET", path="/v1/clusters",
                      summary="list clusters", description=""),
        EndpointEntry(product="vlb", method="GET", path="/v2/loadbalancers",
                      summary="list loadbalancers", description=""),
    ]
    _setup(entries)
    results = search("create list")  # AND: no match. OR: both match on "list".
    assert len(results) == 2


def test_search_ranks_summary_match_higher():
    """Entry with term in summary outranks entry with term only in description."""
    entries = [
        EndpointEntry(product="p1", method="GET", path="/a", summary="something",
                      description="cluster operations"),
        EndpointEntry(product="p2", method="GET", path="/b", summary="manage cluster",
                      description="other"),
    ]
    _setup(entries)
    results = search("cluster")
    assert results[0].summary == "manage cluster"


def test_search_synonym_vpc_matches_network():
    """Query 'vpc' should find endpoints with 'network' (VNG Cloud terminology)."""
    entries = [
        EndpointEntry(product="vserver", method="GET", path="/v2/{projectId}/networks",
                      summary="List networks", description=""),
    ]
    _setup(entries)
    results = search("vpc")
    assert len(results) == 1
    assert results[0].path == "/v2/{projectId}/networks"


def test_search_synonym_instance_matches_server():
    """Query 'instance' should find endpoints with 'server'."""
    entries = [
        EndpointEntry(product="vserver", method="GET", path="/v2/{projectId}/servers",
                      summary="List servers", description=""),
    ]
    _setup(entries)
    assert len(search("instance")) == 1


def test_search_synonym_keeps_and_logic():
    """Multi-term query with synonym: 'list vpc' requires both 'list' AND ('vpc' OR 'network')."""
    entries = [
        EndpointEntry(product="vserver", method="GET", path="/v2/{projectId}/networks",
                      summary="List networks", description=""),
        EndpointEntry(product="vserver", method="POST", path="/v2/{projectId}/servers",
                      summary="Create server", description=""),  # no "list"
    ]
    _setup(entries)
    results = search("list vpc")
    assert len(results) == 1
    assert results[0].path == "/v2/{projectId}/networks"

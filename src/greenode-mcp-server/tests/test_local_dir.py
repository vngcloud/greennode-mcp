"""Tests for LocalDirProvider — reads specs from a filesystem directory."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from greennode.greenode_mcp_server.registry.local_dir import LocalDirProvider
from greennode.greenode_mcp_server.registry.provider import (
    ProductRef,
    SpecFetchError,
)


@pytest.fixture
def specs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "specs"
    d.mkdir()
    (d / "vks.json").write_text(json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "VKS API"},
        "paths": {"/v1/clusters": {"get": {"summary": "list"}}},
    }))
    (d / "vlb.json").write_text(json.dumps({
        "openapi": "3.0.0",
        "info": {"title": "VLB Service API"},
        "paths": {},
    }))
    return d


async def test_list_products_reads_info_title(specs_dir: Path):
    p = LocalDirProvider(specs_dir)
    refs = await p.list_products()
    names = {r.name for r in refs}
    assert names == {"vks", "vlb"}
    vks = next(r for r in refs if r.name == "vks")
    assert vks.display_name == "VKS API"


async def test_list_products_sorted_alphabetically(specs_dir: Path):
    p = LocalDirProvider(specs_dir)
    refs = await p.list_products()
    assert [r.name for r in refs] == sorted(r.name for r in refs)


async def test_fetch_spec_returns_parsed_json(specs_dir: Path):
    p = LocalDirProvider(specs_dir)
    ref = ProductRef(name="vks", display_name="VKS API", source_url=str(specs_dir / "vks.json"))
    spec = await p.fetch_spec(ref)
    assert spec["openapi"] == "3.0.0"
    assert "/v1/clusters" in spec["paths"]


async def test_fetch_spec_missing_file_raises(tmp_path: Path):
    p = LocalDirProvider(tmp_path)
    ref = ProductRef(name="x", display_name="X", source_url=str(tmp_path / "x.json"))
    with pytest.raises(SpecFetchError):
        await p.fetch_spec(ref)


async def test_fetch_spec_invalid_json_raises(tmp_path: Path):
    (tmp_path / "broken.json").write_text("not json {{{")
    p = LocalDirProvider(tmp_path)
    ref = ProductRef(name="broken", display_name="Broken", source_url=str(tmp_path / "broken.json"))
    with pytest.raises(SpecFetchError):
        await p.fetch_spec(ref)


def test_provider_name():
    p = LocalDirProvider(Path("/tmp"))
    assert p.provider_name() == "local-dir"

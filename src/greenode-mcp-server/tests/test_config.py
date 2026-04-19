"""Tests for greenode_mcp_server.config module."""
from __future__ import annotations

import pytest

from greennode.greenode_mcp_server.config import load_config


def test_load_config_with_client_credentials(sample_config):
    cfg = load_config(sample_config)
    assert cfg.client_id == "test-client-id"
    assert cfg.client_secret == "test-client-secret"
    assert cfg.default_region == "HCM-3"


def test_load_config_missing_credentials(tmp_path):
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()
    config = greenode_dir / "config"
    config.write_text("[default]\nregion = HCM-3\n")
    with pytest.raises(FileNotFoundError):
        load_config(greenode_dir)


def test_load_config_missing_client_id(tmp_path):
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()
    credentials = greenode_dir / "credentials"
    credentials.write_text("[default]\nclient_secret = secret\n")
    with pytest.raises(ValueError, match="client_id"):
        load_config(greenode_dir)


def test_get_region_endpoints(sample_config):
    cfg = load_config(sample_config)
    ep = cfg.get_endpoints("HCM-3")
    assert ep.vks == "https://vks.api.vngcloud.vn"
    assert ep.vserver == "https://hcm-3.api.vngcloud.vn/vserver/vserver-gateway"


def test_get_region_endpoints_default(sample_config):
    cfg = load_config(sample_config)
    ep = cfg.get_endpoints()
    assert ep.vks == "https://vks.api.vngcloud.vn"
    assert ep.vserver == "https://hcm-3.api.vngcloud.vn/vserver/vserver-gateway"


def test_get_region_endpoints_han(sample_config):
    cfg = load_config(sample_config)
    ep = cfg.get_endpoints("HAN")
    assert ep.vks == "https://vks-han-1.api.vngcloud.vn"
    assert ep.vserver == "https://han-1.api.vngcloud.vn/vserver/vserver-gateway"


def test_load_config_missing_file(tmp_path):
    missing_dir = tmp_path / "no_such_dir"
    with pytest.raises(FileNotFoundError):
        load_config(missing_dir)


def test_get_endpoints_invalid_region(sample_config):
    cfg = load_config(sample_config)
    with pytest.raises(ValueError, match="does not exist"):
        cfg.get_endpoints("INVALID-REGION")


def test_load_config_default_region_when_no_config_file(tmp_path):
    """When no config file exists, default_region should be HCM-3."""
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()
    credentials = greenode_dir / "credentials"
    credentials.write_text("[default]\nclient_id = my-id\nclient_secret = my-secret\n")
    cfg = load_config(greenode_dir)
    assert cfg.default_region == "HCM-3"


# --- project_id ---

def test_load_config_project_id_from_file(tmp_path):
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()
    (greenode_dir / "credentials").write_text(
        "[default]\nclient_id = id\nclient_secret = secret\n"
    )
    (greenode_dir / "config").write_text(
        "[default]\nregion = HCM-3\nproject_id = pro-from-file\n"
    )
    cfg = load_config(greenode_dir)
    assert cfg.default_project_id == "pro-from-file"


def test_load_config_project_id_env_overrides_file(tmp_path, monkeypatch):
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()
    (greenode_dir / "credentials").write_text(
        "[default]\nclient_id = id\nclient_secret = secret\n"
    )
    (greenode_dir / "config").write_text(
        "[default]\nregion = HCM-3\nproject_id = pro-from-file\n"
    )
    monkeypatch.setenv("GRN_DEFAULT_PROJECT_ID", "pro-from-env")
    cfg = load_config(greenode_dir)
    assert cfg.default_project_id == "pro-from-env"


def test_load_config_project_id_none_when_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("GRN_DEFAULT_PROJECT_ID", raising=False)
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()
    (greenode_dir / "credentials").write_text(
        "[default]\nclient_id = id\nclient_secret = secret\n"
    )
    cfg = load_config(greenode_dir)
    assert cfg.default_project_id is None


def test_load_config_non_default_profile_uses_profile_section(tmp_path, monkeypatch):
    """greenode-cli writes non-default profiles under '[profile <name>]'."""
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()
    (greenode_dir / "credentials").write_text(
        "[work]\nclient_id = work-id\nclient_secret = work-secret\n"
    )
    (greenode_dir / "config").write_text(
        "[profile work]\nregion = HAN\nproject_id = pro-work\n"
    )
    monkeypatch.setenv("GRN_PROFILE", "work")
    cfg = load_config(greenode_dir)
    assert cfg.default_region == "HAN"
    assert cfg.default_project_id == "pro-work"

"""Tests for the env-driven passthrough config."""

from greennode.agentbase_mcp_server.config import (
    BASE_URLS,
    SERVICES,
    AgentbaseConfig,
    load_config,
)


def test_services_covers_all_six():
    assert SERVICES == ("policy", "cr", "gateway", "identity", "memory", "runtime")


def test_base_urls_cover_all_services():
    for svc in SERVICES:
        assert svc in BASE_URLS
        assert BASE_URLS[svc].startswith("https://")


def test_get_base_url_returns_service_url():
    cfg = AgentbaseConfig(default_region="prod", base_urls=dict(BASE_URLS))
    assert cfg.get_base_url(None, "policy") == BASE_URLS["policy"]
    assert cfg.get_base_url("anything", "memory") == BASE_URLS["memory"]


def test_load_config_reads_env_override(monkeypatch):
    monkeypatch.setenv("AGENTBASE_POLICY_BASE_URL", "https://custom.example/policy")
    cfg = load_config()
    assert cfg.get_base_url(None, "policy") == "https://custom.example/policy"
    # Untouched services keep defaults.
    assert cfg.get_base_url(None, "memory") == BASE_URLS["memory"]


def test_load_config_default_region(monkeypatch):
    monkeypatch.delenv("AGENTBASE_DEFAULT_REGION", raising=False)
    cfg = load_config()
    assert cfg.default_region == "prod"

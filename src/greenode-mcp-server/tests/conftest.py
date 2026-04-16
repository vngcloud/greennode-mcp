"""Pytest fixtures for GreenNode MCP Server tests."""

import pytest


@pytest.fixture
def sample_config(tmp_path):
    """Fake greenode directory with credentials and config INI files."""
    greenode_dir = tmp_path / ".greenode"
    greenode_dir.mkdir()

    credentials = greenode_dir / "credentials"
    credentials.write_text(
        "[default]\n"
        "client_id = test-client-id\n"
        "client_secret = test-client-secret\n"
    )

    config = greenode_dir / "config"
    config.write_text(
        "[default]\n"
        "region = HCM-3\n"
        "output = json\n"
    )

    return greenode_dir

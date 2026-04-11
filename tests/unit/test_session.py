from __future__ import annotations

import configparser
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from grncli.session import Session


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary ~/.greenode/ directory with config + credentials."""
    credentials = tmp_path / "credentials"
    credentials.write_text(
        "[default]\n"
        "client_id = default-id\n"
        "client_secret = default-secret\n"
        "\n"
        "[staging]\n"
        "client_id = staging-id\n"
        "client_secret = staging-secret\n"
    )
    config = tmp_path / "config"
    config.write_text(
        "[default]\n"
        "region = HCM-3\n"
        "output = json\n"
        "\n"
        "[profile staging]\n"
        "region = HAN\n"
        "output = table\n"
    )
    return tmp_path


class TestSessionCredentials:
    def test_load_default_credentials(self, config_dir):
        session = Session(config_dir=str(config_dir))
        creds = session.get_credentials()
        assert creds['client_id'] == 'default-id'
        assert creds['client_secret'] == 'default-secret'

    def test_load_profile_credentials(self, config_dir):
        session = Session(config_dir=str(config_dir), profile='staging')
        creds = session.get_credentials()
        assert creds['client_id'] == 'staging-id'
        assert creds['client_secret'] == 'staging-secret'

    def test_env_vars_override_file(self, config_dir):
        with patch.dict(os.environ, {
            'GRN_CLIENT_ID': 'env-id',
            'GRN_CLIENT_SECRET': 'env-secret',
        }):
            session = Session(config_dir=str(config_dir))
            creds = session.get_credentials()
            assert creds['client_id'] == 'env-id'
            assert creds['client_secret'] == 'env-secret'

    def test_missing_credentials_raises(self, tmp_path):
        session = Session(config_dir=str(tmp_path))
        with pytest.raises(Exception, match="credentials"):
            session.get_credentials()


class TestSessionConfig:
    def test_load_default_config(self, config_dir):
        session = Session(config_dir=str(config_dir))
        assert session.get_config_variable('region') == 'HCM-3'
        assert session.get_config_variable('output') == 'json'

    def test_load_profile_config(self, config_dir):
        session = Session(config_dir=str(config_dir), profile='staging')
        assert session.get_config_variable('region') == 'HAN'
        assert session.get_config_variable('output') == 'table'

    def test_env_var_region_override(self, config_dir):
        with patch.dict(os.environ, {'GRN_DEFAULT_REGION': 'HAN'}):
            session = Session(config_dir=str(config_dir))
            assert session.get_config_variable('region') == 'HAN'

    def test_env_var_output_override(self, config_dir):
        with patch.dict(os.environ, {'GRN_DEFAULT_OUTPUT': 'table'}):
            session = Session(config_dir=str(config_dir))
            assert session.get_config_variable('output') == 'table'

    def test_env_var_profile(self, config_dir):
        with patch.dict(os.environ, {'GRN_PROFILE': 'staging'}):
            session = Session(config_dir=str(config_dir))
            assert session.get_config_variable('region') == 'HAN'


class TestSessionEndpoints:
    def test_get_endpoint_hcm3(self, config_dir):
        session = Session(config_dir=str(config_dir))
        endpoint = session.get_endpoint('vks')
        assert endpoint == 'https://vks.api.vngcloud.vn'

    def test_get_endpoint_han(self, config_dir):
        session = Session(config_dir=str(config_dir), profile='staging')
        endpoint = session.get_endpoint('vks')
        assert endpoint == 'https://vks-han-1.api.vngcloud.vn'

    def test_get_scoped_config(self, config_dir):
        session = Session(config_dir=str(config_dir))
        config = session.get_scoped_config()
        assert config['region'] == 'HCM-3'
        assert config['output'] == 'json'

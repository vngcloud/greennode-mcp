# greenode-cli/tests/functional/test_cli_integration.py
from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest
import respx

from grncli.clidriver import main

IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"
VKS_URL = "https://vks.api.vngcloud.vn"


@pytest.fixture
def greenode_config(tmp_path):
    """Setup a complete greenode config."""
    creds = tmp_path / "credentials"
    creds.write_text("[default]\nclient_id = test-id\nclient_secret = test-secret\n")

    config = tmp_path / "config"
    config.write_text("[default]\nregion = HCM-3\noutput = json\n")

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop('GRN_CLIENT_ID', None)
        os.environ.pop('GRN_CLIENT_SECRET', None)
        os.environ.pop('GRN_DEFAULT_REGION', None)
        os.environ.pop('GRN_PROFILE', None)

    return str(tmp_path)


class TestCLIIntegration:
    @respx.mock
    def test_list_clusters_json(self, greenode_config, capsys):
        respx.post(IAM_URL).mock(return_value=httpx.Response(
            200, json={"accessToken": "tok", "expiresIn": 3600}
        ))
        respx.get(f"{VKS_URL}/v1/clusters").mock(return_value=httpx.Response(
            200, json={"items": [{"id": "c-1", "name": "prod"}], "total": 1}
        ))

        with patch('grncli.session.DEFAULT_CONFIG_DIR', greenode_config):
            rc = main(['vks', 'list-clusters'])

        assert rc == 0
        captured = capsys.readouterr()
        assert 'prod' in captured.out

    @respx.mock
    def test_get_cluster(self, greenode_config, capsys):
        respx.post(IAM_URL).mock(return_value=httpx.Response(
            200, json={"accessToken": "tok", "expiresIn": 3600}
        ))
        respx.get(f"{VKS_URL}/v1/clusters/c-1").mock(
            return_value=httpx.Response(
                200, json={"id": "c-1", "name": "prod", "status": "ACTIVE"}
            )
        )

        with patch('grncli.session.DEFAULT_CONFIG_DIR', greenode_config):
            rc = main(['vks', 'get-cluster', '--cluster-id', 'c-1'])

        assert rc == 0
        captured = capsys.readouterr()
        assert 'ACTIVE' in captured.out

    def test_configure_interactive(self, greenode_config, tmp_path):
        with patch('grncli.session.DEFAULT_CONFIG_DIR', greenode_config):
            with patch('builtins.input', side_effect=[
                'my-id', 'my-secret', 'HCM-3', 'json'
            ]):
                rc = main(['configure'])

        assert rc == 0
        creds = (tmp_path / "credentials").read_text()
        assert 'my-id' in creds

    def test_unknown_command_returns_255(self, greenode_config):
        with patch('grncli.session.DEFAULT_CONFIG_DIR', greenode_config):
            rc = main(['nonexistent'])
        assert rc == 255

    def test_version(self, greenode_config):
        with patch('grncli.session.DEFAULT_CONFIG_DIR', greenode_config):
            with pytest.raises(SystemExit) as exc:
                main(['--version'])
            assert exc.value.code == 0

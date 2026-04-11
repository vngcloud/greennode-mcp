# greenode-cli/tests/unit/test_configure.py
from __future__ import annotations

from unittest.mock import MagicMock
from argparse import Namespace

import pytest

from grncli.customizations.configure.configure import ConfigureCommand


@pytest.fixture
def session(tmp_path):
    s = MagicMock()
    s.config_dir = str(tmp_path)
    s.credentials_file = str(tmp_path / "credentials")
    s.config_file = str(tmp_path / "config")
    s.profile = 'default'
    s.get_scoped_config.return_value = {}
    s.get_credentials.side_effect = FileNotFoundError
    return s


class TestConfigureCommand:
    def test_interactive_prompts(self, session):
        prompter = MagicMock()
        prompter.get_value.side_effect = ['my-id', 'my-secret', 'HCM-3', 'json']
        cmd = ConfigureCommand(session, prompter=prompter)
        parsed_globals = Namespace(profile=None)
        rc = cmd._run_main(Namespace(), parsed_globals)
        assert rc == 0
        assert prompter.get_value.call_count == 4

    def test_writes_credentials_file(self, session, tmp_path):
        prompter = MagicMock()
        prompter.get_value.side_effect = ['new-id', 'new-secret', 'HCM-3', 'json']
        cmd = ConfigureCommand(session, prompter=prompter)
        parsed_globals = Namespace(profile=None)
        cmd._run_main(Namespace(), parsed_globals)
        creds = (tmp_path / "credentials").read_text()
        assert 'new-id' in creds
        assert 'new-secret' in creds

    def test_writes_config_file(self, session, tmp_path):
        prompter = MagicMock()
        prompter.get_value.side_effect = ['id', 'secret', 'HCM-3', 'json']
        cmd = ConfigureCommand(session, prompter=prompter)
        parsed_globals = Namespace(profile=None)
        cmd._run_main(Namespace(), parsed_globals)
        config = (tmp_path / "config").read_text()
        assert 'HCM-3' in config
        assert 'json' in config

    def test_has_subcommands(self, session):
        cmd = ConfigureCommand(session)
        assert len(cmd.SUBCOMMANDS) == 3

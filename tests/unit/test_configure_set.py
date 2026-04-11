# greenode-cli/tests/unit/test_configure_set.py
from __future__ import annotations

from argparse import Namespace
from unittest.mock import MagicMock

from grncli.customizations.configure.set import ConfigureSetCommand


class TestConfigureSet:
    def test_set_config_value(self):
        session = MagicMock()
        session.profile = 'default'
        session.config_file = '/fake/config'
        writer = MagicMock()
        cmd = ConfigureSetCommand(session, config_writer=writer)

        rc = cmd._run_main(Namespace(varname='region', value='HAN'), Namespace(profile=None))
        assert rc == 0
        writer.update_config.assert_called_once_with(
            {'__section__': 'default', 'region': 'HAN'}, '/fake/config',
        )

    def test_set_credential_value(self):
        session = MagicMock()
        session.profile = 'default'
        session.credentials_file = '/fake/credentials'
        writer = MagicMock()
        cmd = ConfigureSetCommand(session, config_writer=writer)

        rc = cmd._run_main(Namespace(varname='client_id', value='new-id'), Namespace(profile=None))
        assert rc == 0
        writer.update_config.assert_called_once_with(
            {'__section__': 'default', 'client_id': 'new-id'}, '/fake/credentials',
        )

    def test_set_with_profile_dotted(self):
        session = MagicMock()
        session.profile = 'default'
        session.config_file = '/fake/config'
        writer = MagicMock()
        cmd = ConfigureSetCommand(session, config_writer=writer)

        rc = cmd._run_main(Namespace(varname='profile.staging.output', value='table'), Namespace(profile=None))
        assert rc == 0
        writer.update_config.assert_called_once_with(
            {'__section__': 'profile staging', 'output': 'table'}, '/fake/config',
        )

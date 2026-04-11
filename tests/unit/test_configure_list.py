# greenode-cli/tests/unit/test_configure_list.py
from __future__ import annotations

import io
import sys
from argparse import Namespace
from unittest.mock import MagicMock

from grncli.customizations.configure.list import ConfigureListCommand


class TestConfigureList:
    def test_shows_all_fields(self):
        session = MagicMock()
        session.profile = 'default'
        session.get_credentials.return_value = {
            'client_id': 'abcdef1234567890',
            'client_secret': 'secret1234567890',
        }
        session.get_scoped_config.return_value = {'region': 'HCM-3', 'output': 'json'}
        session.credentials_file = '~/.greenode/credentials'
        session.config_file = '~/.greenode/config'

        cmd = ConfigureListCommand(session)
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(), Namespace(profile=None))
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        assert rc == 0
        assert 'client_id' in output
        assert 'client_secret' in output
        assert 'region' in output
        assert 'HCM-3' in output
        assert '****************7890' in output

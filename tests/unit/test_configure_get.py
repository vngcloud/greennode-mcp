# greenode-cli/tests/unit/test_configure_get.py
from __future__ import annotations

import io
import sys
from argparse import Namespace
from unittest.mock import MagicMock

from grncli.customizations.configure.get import ConfigureGetCommand


class TestConfigureGet:
    def test_get_simple_value(self):
        session = MagicMock()
        session.get_scoped_config.return_value = {'region': 'HCM-3'}
        session.get_credentials.return_value = {}
        cmd = ConfigureGetCommand(session)

        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            rc = cmd._run_main(Namespace(varname='region'), Namespace(profile=None))
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

        assert rc == 0
        assert 'HCM-3' in output

    def test_get_missing_returns_1(self):
        session = MagicMock()
        session.get_scoped_config.return_value = {}
        session.get_credentials.return_value = {}
        cmd = ConfigureGetCommand(session)

        rc = cmd._run_main(Namespace(varname='nonexistent'), Namespace(profile=None))
        assert rc == 1

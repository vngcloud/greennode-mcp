# greenode-cli/tests/unit/test_clidriver.py
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest

from grncli.clidriver import CLIDriver, create_clidriver, main


class TestCLIDriver:
    def test_create_clidriver(self):
        with patch('grncli.clidriver.Session') as MockSession:
            with patch('grncli.clidriver.load_plugins'):
                driver = create_clidriver()
                assert isinstance(driver, CLIDriver)

    def test_version(self):
        with patch('grncli.clidriver.Session') as MockSession:
            with patch('grncli.clidriver.load_plugins'):
                driver = create_clidriver()
                with pytest.raises(SystemExit) as exc_info:
                    driver.main(['--version'])
                assert exc_info.value.code == 0

    def test_unknown_command(self):
        with patch('grncli.clidriver.Session') as MockSession:
            with patch('grncli.clidriver.load_plugins'):
                driver = create_clidriver()
                rc = driver.main(['nonexistent-command'])
                assert rc == 255

    def test_no_args_shows_usage(self):
        with patch('grncli.clidriver.Session') as MockSession:
            with patch('grncli.clidriver.load_plugins'):
                driver = create_clidriver()
                rc = driver.main([])
                assert rc == 0

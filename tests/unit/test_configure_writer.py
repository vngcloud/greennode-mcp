from __future__ import annotations

import os
import platform
import stat

import pytest

import pytest

from grncli.customizations.configure.writer import ConfigFileWriter


class TestConfigFileWriter:
    def test_create_new_file(self, tmp_path):
        config_file = str(tmp_path / "config")
        writer = ConfigFileWriter()
        writer.update_config(
            {'region': 'HCM-3', 'output': 'json'},
            config_file,
        )
        content = open(config_file).read()
        assert '[default]' in content
        assert 'region = HCM-3' in content
        assert 'output = json' in content

    @pytest.mark.skipif(platform.system() == 'Windows', reason='Unix permissions not supported on Windows')
    def test_file_permissions(self, tmp_path):
        config_file = str(tmp_path / "credentials")
        writer = ConfigFileWriter()
        writer.update_config({'client_id': 'abc'}, config_file)
        mode = os.stat(config_file).st_mode
        assert stat.S_IMODE(mode) == 0o600

    def test_update_existing_value(self, tmp_path):
        config_file = str(tmp_path / "config")
        with open(config_file, 'w') as f:
            f.write("[default]\nregion = HCM-3\noutput = json\n")
        writer = ConfigFileWriter()
        writer.update_config({'region': 'HAN'}, config_file)
        content = open(config_file).read()
        assert 'region = HAN' in content
        assert 'region = HCM-3' not in content
        assert 'output = json' in content

    def test_write_to_profile_section(self, tmp_path):
        config_file = str(tmp_path / "config")
        writer = ConfigFileWriter()
        writer.update_config(
            {'__section__': 'profile staging', 'region': 'HAN'},
            config_file,
        )
        content = open(config_file).read()
        assert '[profile staging]' in content
        assert 'region = HAN' in content

    def test_add_to_existing_section(self, tmp_path):
        config_file = str(tmp_path / "config")
        with open(config_file, 'w') as f:
            f.write("[default]\nregion = HCM-3\n")
        writer = ConfigFileWriter()
        writer.update_config({'output': 'table'}, config_file)
        content = open(config_file).read()
        assert 'region = HCM-3' in content
        assert 'output = table' in content

    def test_preserve_comments(self, tmp_path):
        config_file = str(tmp_path / "config")
        with open(config_file, 'w') as f:
            f.write("# This is a comment\n[default]\nregion = HCM-3\n")
        writer = ConfigFileWriter()
        writer.update_config({'output': 'json'}, config_file)
        content = open(config_file).read()
        assert '# This is a comment' in content

    def test_reject_newline_in_value(self, tmp_path):
        config_file = str(tmp_path / "config")
        writer = ConfigFileWriter()
        with pytest.raises(ValueError, match="newline"):
            writer.update_config({'region': 'HCM\n-3'}, config_file)

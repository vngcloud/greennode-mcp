from __future__ import annotations

import os
import re


class ConfigFileWriter:
    """Read/write INI config files (similar to AWS CLI ConfigFileWriter)."""

    SECTION_REGEX = re.compile(r'^\s*\[(?P<header>[^]]+)\]')
    OPTION_REGEX = re.compile(
        r'(?P<option>[^:=\s][^:=]*)\s*(?P<vi>[:=])\s*(?P<value>.*)$'
    )

    def update_config(
        self,
        new_values: dict[str, str],
        config_filename: str,
    ) -> None:
        section_name = new_values.pop('__section__', 'default')

        for key, value in new_values.items():
            if '\n' in str(key) or '\r' in str(key):
                raise ValueError(f"Key contains newline: {key}")
            if '\n' in str(value) or '\r' in str(value):
                raise ValueError(f"Value contains newline: {value}")

        if not os.path.isfile(config_filename):
            self._create_file(config_filename)
            self._write_new_section(section_name, new_values, config_filename)
            return

        with open(config_filename, 'r') as f:
            contents = f.readlines()

        if self._update_section_contents(contents, section_name, new_values):
            with open(config_filename, 'w') as f:
                f.write(''.join(contents))
        else:
            self._write_new_section(section_name, new_values, config_filename)

    def _create_file(self, filename: str) -> None:
        dirname = os.path.dirname(filename)
        if dirname and not os.path.isdir(dirname):
            os.makedirs(dirname, mode=0o700, exist_ok=True)
        with open(filename, 'w') as f:
            pass
        os.chmod(filename, 0o600)

    def _write_new_section(
        self,
        section_name: str,
        values: dict[str, str],
        filename: str,
    ) -> None:
        with open(filename, 'a') as f:
            f.write(f'[{section_name}]\n')
            for key, value in values.items():
                f.write(f'{key} = {value}\n')

    def _update_section_contents(
        self,
        contents: list[str],
        section_name: str,
        new_values: dict[str, str],
    ) -> bool:
        values_to_set = dict(new_values)
        in_section = False
        section_end_idx = len(contents)

        for i, line in enumerate(contents):
            match = self.SECTION_REGEX.match(line)
            if match:
                if in_section:
                    section_end_idx = i
                    break
                if match.group('header').strip() == section_name:
                    in_section = True
                continue

            if in_section:
                opt_match = self.OPTION_REGEX.match(line)
                if opt_match:
                    key = opt_match.group('option').strip()
                    if key in values_to_set:
                        contents[i] = f'{key} = {values_to_set.pop(key)}\n'

        if not in_section:
            return False

        if values_to_set:
            insert_lines = [
                f'{key} = {value}\n' for key, value in values_to_set.items()
            ]
            contents[section_end_idx:section_end_idx] = insert_lines

        return True

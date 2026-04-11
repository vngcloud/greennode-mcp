from __future__ import annotations

import importlib
import logging

log = logging.getLogger(__name__)

BUILTIN_PLUGINS = {'__builtin__': 'grncli.handlers'}


def load_plugins(plugin_mapping: dict[str, str], event_hooks=None,
                 include_builtins: bool = True) -> None:
    if include_builtins:
        plugin_mapping = {**BUILTIN_PLUGINS, **plugin_mapping}

    for name, module_path in plugin_mapping.items():
        log.debug("Loading plugin %s: %s", name, module_path)
        module = importlib.import_module(module_path)
        module.grncli_initialize(event_hooks)

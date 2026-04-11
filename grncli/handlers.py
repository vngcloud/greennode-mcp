from __future__ import annotations


def grncli_initialize(event_hooks):
    """Register all built-in customizations."""
    from grncli.customizations.configure import register_configure_cmd
    register_configure_cmd(event_hooks)

    from grncli.customizations.vks import register_vks_commands
    register_vks_commands(event_hooks)

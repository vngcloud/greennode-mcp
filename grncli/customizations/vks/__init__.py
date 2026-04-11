from __future__ import annotations


def register_vks_commands(event_hooks):
    event_hooks.register('building-command-table.main', _inject_vks_service)
    event_hooks.register('building-command-table.vks', _inject_vks_operations)


def _inject_vks_service(command_table, session, **kwargs):
    from grncli.clidriver import ServiceCommand
    command_table['vks'] = ServiceCommand('vks', session)


def _inject_vks_operations(command_table, session, **kwargs):
    from grncli.customizations.vks.list_clusters import ListClustersCommand
    from grncli.customizations.vks.get_cluster import GetClusterCommand
    from grncli.customizations.vks.create_cluster import CreateClusterCommand
    from grncli.customizations.vks.update_cluster import UpdateClusterCommand
    from grncli.customizations.vks.delete_cluster import DeleteClusterCommand
    from grncli.customizations.vks.list_nodegroups import ListNodegroupsCommand
    from grncli.customizations.vks.get_nodegroup import GetNodegroupCommand
    from grncli.customizations.vks.create_nodegroup import CreateNodegroupCommand
    from grncli.customizations.vks.update_nodegroup import UpdateNodegroupCommand
    from grncli.customizations.vks.delete_nodegroup import DeleteNodegroupCommand
    from grncli.customizations.vks.wait import WaitClusterActiveCommand

    command_table['list-clusters'] = ListClustersCommand(session)
    command_table['get-cluster'] = GetClusterCommand(session)
    command_table['create-cluster'] = CreateClusterCommand(session)
    command_table['update-cluster'] = UpdateClusterCommand(session)
    command_table['delete-cluster'] = DeleteClusterCommand(session)
    command_table['list-nodegroups'] = ListNodegroupsCommand(session)
    command_table['get-nodegroup'] = GetNodegroupCommand(session)
    command_table['create-nodegroup'] = CreateNodegroupCommand(session)
    command_table['update-nodegroup'] = UpdateNodegroupCommand(session)
    command_table['delete-nodegroup'] = DeleteNodegroupCommand(session)
    command_table['wait-cluster-active'] = WaitClusterActiveCommand(session)

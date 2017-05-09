"""Installs and configures Treadmill locally."""

import os

import click
import yaml

import treadmill
from treadmill import bootstrap
from treadmill.bootstrap.linux_bootstrap import NodeBootstrap, MasterBootstrap
from treadmill.bootstrap.linux_bootstrap import HAProxyBootstrap, SpawnBootstrap
from treadmill import cli
from treadmill import context


def _load_configs(config, default_file):
    allconfigs = [
        os.path.join(treadmill.TREADMILL, 'etc/linux.aliases'),
        os.path.join(treadmill.TREADMILL, default_file)
    ]

    for filename in config:
        allconfigs.append(filename)

    params = {}
    for filename in allconfigs:
        with open(filename) as f:
            params.update(yaml.load(f.read()))

    return params


def _load_ldap_config():
    """Parameters for both node and master."""
    cellname = context.GLOBAL.cell
    admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
    return {
        'cell': cellname,
        'zookeeper': context.GLOBAL.zk.url,
        'ldap': context.GLOBAL.ldap.url,
        'dns_domain': context.GLOBAL.dns_domain,
        'ldap_search_base': context.GLOBAL.ldap.search_base,
        'treadmill': treadmill.TREADMILL,
        'treadmillid': params['username']
    }


def init():
    """Return top level command handler."""

    @click.group()
    @click.option('--zookeeper', required=False,
                  envvar='TREADMILL_ZOOKEEPER',
                  callback=cli.handle_context_opt,
                  expose_value=False)
    @click.option('--cell', required=True,
                  envvar='TREADMILL_CELL',
                  callback=cli.handle_context_opt,
                  expose_value=False)
    @click.pass_context
    @click.option('--aliases', type=click.File(), multiple=True)
    @click.pass_context
    def install(ctx, aliases):
        """Installs Treadmill."""

        aliases_path = ":".join(
            [os.path.abspath(x.name) for x in aliases])

        linux_aliases = os.path.join(treadmill.TREADMILL, 'etc/linux.aliases')
        aliases_path = linux_aliases + ':' + aliases_path
        ctx.obj['COMMON_DEFAULTS'] = {
            'aliases_path': aliases_path
        }

        aliases_data = {}
        for conf in aliases:
            aliases_data.update(yaml.load(conf.read()))
        with open(linux_aliases) as f:
            aliases_data.update(yaml.load(f.read()))

        ctx.obj['COMMON_DEFAULTS']['_alias'] = aliases_data
        # TODO(boysson): remove the below once all templates are cleaned up
        ctx.obj['COMMON_DEFAULTS'].update(aliases_data)

        for conf in config:
            ctx.obj['COMMON_DEFAULTS'].update(yaml.load(stream=conf))

        if override:
            ctx.obj['COMMON_DEFAULTS'].update(override)

        os.environ['TREADMILL'] = treadmill.TREADMILL
        os.environ['TREADMILL_ALIASES_PATH'] = aliases_path

    @install.command()
    @click.option('--install-dir',
                  default=lambda: os.path.join(bootstrap.DEFAULT_INSTALL_DIR,
                                               "treadmill"))
    @click.option('--run/--no-run', is_flag=True, default=False)
    @click.option('--config', type=click.File(), multiple=True)
    @click.option('--override', required=False, type=cli.DICT)
    @click.option('--use-ldap', is_flag=True, default=False)
    @click.pass_context
    def node(ctx, install_dir, run, config, override, use_ldap):
        """Installs Treadmill node."""

        node_config = 'local/linux/node.config.yml'
        params = _load_configs(config, node_config)
        if override:
             params.update(override)

        params.update({'dir': install_dir})

        if use_ldap:
            params.update(_load_ldap_config())

        node_bootstrap = bootstrap.NodeBootstrap(
            install_dir,
            params,
        )

        node_bootstrap.install()

        if run:
            node_bootstrap.run()

    del node

    if os.name != 'nt':
        @install.command()
        @click.option('--install-dir',
                      default=lambda: os.path.join(
                          bootstrap.DEFAULT_INSTALL_DIR,
                          "treadmill_master"))
        @click.option('--run/--no-run', is_flag=True, default=False)
        @click.option('--master-id', required=True,
                      type=click.Choice(['1', '2', '3']))
        @click.option('--config', type=click.File(), multiple=True)
        @click.option('--override', required=False, type=cli.DICT)
        @click.option('--use-ldap', is_flag=True, default=False)
        @click.pass_context
        def master(ctx, install_dir, run, master_id, config, overrride, use_ldap):
            """Installs Treadmill master."""

            master_config_file = 'local/linux/master.config.yml'

            params = _load_configs(config, master_config_file)
            if use_ldap:
                params.update(_load_ldap_config())
            if override:
                params.update(override)


            params.update({
                'master-id': master_id,
                'dir': os.path.join(
                    install_dir,
                    os.environ.get('TREADMILL_CELL'),
                    master_id)
            })
            for master in params['masters']:  # pylint: disable=E1136
                if master['idx'] == int(master_id):
                    params.update({'me': master})

            master_bootstrap = bootstrap.MasterBootstrap(
                install_dir,
                params,
                master_id
            )
            master_bootstrap.install()

            if run:
                master_bootstrap.run()

        del master

        @install.command()
        @click.option('--install-dir',
                      default=lambda: os.path.join(
                          bootstrap.DEFAULT_INSTALL_DIR,
                          "treadmill_spawn"))
        @click.option('--run/--no-run', is_flag=True, default=False)
        @click.option('--override', required=False, type=cli.DICT)
        @click.pass_context
        def spawn(ctx, install_dir, run):
            """Installs Treadmill spawn."""
            if override:
                ctx.obj['COMMON_DEFAULTS'].update(override)
            spawn_bootstrap = bootstrap.SpawnBootstrap(
                install_dir,
                ctx.obj['COMMON_DEFAULTS']
            )

            spawn_bootstrap.install()

            if run:
                spawn_bootstrap.run()

        del spawn

        @install.command()
        @click.option('--install-dir',
                      default=lambda: os.path.join(
                          bootstrap.DEFAULT_INSTALL_DIR,
                          "treadmill_haproxy"))
        @click.option('--run/--no-run', is_flag=True, default=False)
        @click.option('--override', required=False, type=cli.DICT)
        @click.pass_context
        def haproxy(ctx, install_dir, run):
            """Installs Treadmill haproxy."""
            if override:
                ctx.obj['COMMON_DEFAULTS'].update(override)
            haproxy_bootstrap = bootstrap.HAProxyBootstrap(
                install_dir,
                ctx.obj['COMMON_DEFAULTS']
            )

            haproxy_bootstrap.install()

            if run:
                haproxy_bootstrap.run()

        del haproxy

    return install

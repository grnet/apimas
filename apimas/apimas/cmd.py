import click
from os.path import abspath, dirname, join
from click import types
from apimas import config
from apimas.errors import GenericInputError
from apimas.cli.adapter import ApimasCliAdapter
from apimas.clients.adapter import ApimasClientAdapter


def _construct_cli(root_url, spec):
    client_gen = ApimasClientAdapter(root_url)
    client_gen.construct(spec)
    cli = ApimasCliAdapter(client_gen.get_clients())
    cli.construct(spec)
    return cli


class ApimasCLI(click.MultiCommand):

    def get_command(self, ctx, name):
        config_file = ctx.params.get('config')
        try:
            conf = config.configure(path=config_file)
        except GenericInputError as e:
            raise click.BadOptionUsage(str(e))
        root_url, spec = conf['root'], conf['spec']
        cli = _construct_cli(root_url, spec)
        if name is None:
            return cli.get_base_command()
        return cli.endpoint_groups.get(name)


def print_version():
    version_file_name = 'version.txt'
    version_file = join(dirname(abspath(__file__)), '..',
                        version_file_name)
    with open(version_file) as f:
        package_info = f.read().replace('\n', '')
        click.echo(package_info)


@click.group(cls=ApimasCLI, invoke_without_command=True)
@click.option('--config', type=types.Path(exists=False),
              envvar='APIMAS_CONFIG')
@click.option('--version', '-v', is_flag=True)
@click.pass_context
def apimas(ctx, config, version):
    if version:
        print_version()
    os_args = click.get_os_args()
    if not os_args or os_args[-1] == config:
        cmd = ctx.command.get_command(ctx, None)
        click.echo(cmd.get_help(ctx))


def main():
    apimas()


if __name__ == '__main__':
    main()

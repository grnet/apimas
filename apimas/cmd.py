import click
from click import types
from apimas import config, exceptions as ex
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
        except ex.ApimasException as e:
            raise click.BadOptionUsage(str(e))
        root_url, spec = conf['root'], conf['spec']
        cli = _construct_cli(root_url, spec)
        if name is None:
            return cli.get_base_command()
        return cli.endpoint_groups.get(name)


@click.group(cls=ApimasCLI, invoke_without_command=True)
@click.option('--config', type=types.Path(exists=False),
              envvar='APIMAS_CONFIG')
@click.pass_context
def apimas(ctx, config):
    os_args = click.get_os_args()
    if not os_args or os_args[-1] == config:
        cmd = ctx.command.get_command(ctx, None)
        click.echo(cmd.get_help(ctx))


def main():
    apimas()


if __name__ == '__main__':
    main()

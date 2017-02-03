from apimas import utils
from apimas.cli.adapter import ApimasCliAdapter
from apimas.clients.adapter import ApimasClientAdapter


def main():
    data = utils.load_config()
    root_url = data['root']
    spec = data['spec']
    client_gen = ApimasClientAdapter(root_url)
    client_gen.construct(spec)
    cli = ApimasCliAdapter(client_gen.get_clients())
    cli.construct(spec)
    base_command = cli.get_base_command()
    base_command()


if __name__ == '__main__':
    main()

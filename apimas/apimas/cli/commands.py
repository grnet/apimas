import json
import click
from apimas import documents as doc, exceptions as ex


def is_empty(v):
    return not v and v != 0


def handle_exception(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except ex.ApimasClientException as e:
            if isinstance(e.message, dict):
                click.secho(json.dumps(e.message, indent=2), fg='red')
            else:
                click.secho(e.message, fg='red')
    return wrapper


class BaseCommand(object):
    """ Base class that all commands derive from. """
    def __init__(self, client):
        self.client = client
        self.option_mapping = {}

    def register_option_mapping(self, option_name, path):
        """
        Register a new mapping rule.

        Typically, a mapping rule is consisted of a key corresponding to
        the option name and its path to the data document.

        Example:
        'cart-id': ['cart', 'id']

        The above example illustrates that the option `cart-id` corresponds
        to the path `path/id` of the data document.
        """
        self.option_mapping[option_name] = path

    def options_to_data(self, option_data):
        """
        This method converts option data to the data dictionary that would
        be included to the subsequent HTTP request.

        This conversion regards to the mapping (if exists) of options and
        paths.

        :param option_data: Dictionary keyed by option name and it contains
        its value given by user.
        """
        data = {'/'.join(
            self.option_mapping[k]): list(v) if type(v) is tuple else v
                for k, v in option_data.iteritems() if not is_empty(v)}
        return doc.doc_from_ns(data)

    def add_credentials(self, data):
        """
        Method that adds credentials to the client object in order to
        interact with the API.

        Both authentication mode and schema must be provide. These are derived
        by a configuration file.
        """
        auth_type, credentials = data.pop('credentials', (None, None))
        if not auth_type and not credentials:
            return
        self.client.set_credentials(auth_type, **credentials)

    def format_response(self, data, format_type):
        """
        Print output either in `JSON` or tabular format.

        :param data: Data to be printed.
        :param format_type: Output format type. 'json' or `table`.
        """
        if format_type == 'json':
            click.echo(json.dumps(data, indent=2))
        else:
            from tabulate import tabulate
            if type(data) is dict:
                headers = data.keys()
                table_data = [data.values()]
            else:
                headers = data[0].keys()
                table_data = [obj.values() for obj in data]
            click.echo(tabulate(table_data, headers=headers))

    def __call__(self, **kwargs):
        raise NotImplementedError('__call__() must be implemented.')


class CreateCommand(BaseCommand):
    """
    Command to perform a POST request for the creation of a resource.
    """

    @handle_exception
    def __call__(self, **kwargs):
        self.add_credentials(kwargs)
        data = self.options_to_data(kwargs)
        response = self.client.create(data=data)
        click.echo(json.dumps(response.json(), indent=2))


class UpdateCommand(BaseCommand):
    """
    Command to perform a PATCH request for the update of a specific
    resource.
    """

    @handle_exception
    def __call__(self, resource_id, **kwargs):
        self.add_credentials(kwargs)
        data = self.options_to_data(kwargs)
        response = self.client.partial_update(resource_id, data=data)
        click.echo(json.dumps(response.json(), indent=2))


class RetrieveCommand(BaseCommand):
    """
    Command to perform a `GET` request for the retrieval of a specific
    resource.
    """

    @handle_exception
    def __call__(self, resource_id, **kwargs):
        format_type = kwargs.pop('format')
        self.add_credentials(kwargs)
        data = self.options_to_data(kwargs)
        response = self.client.retrieve(resource_id, params=data)
        self.format_response(response.json(), format_type)


class ListCommand(BaseCommand):
    """
    Command to perform a `GET` request for the listing of a collection of
    resources.
    """

    @handle_exception
    def __call__(self, **kwargs):
        format_type = kwargs.pop('format')
        self.add_credentials(kwargs)
        data = self.options_to_data(kwargs)
        response = self.client.list(params=data)
        self.format_response(response.json(), format_type)


def abort_if_false(ctx, param, value):
    if not value:
        ctx.abort()


class DeleleCommand(BaseCommand):
    """
    Command to perform a `DELETE` request for the deletion of a specific
    resource.
    """

    @handle_exception
    def __call__(self, resource_id, **kwargs):
        self.add_credentials(kwargs)
        self.client.delete(resource_id)

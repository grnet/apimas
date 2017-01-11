import json
import functools
import click
from click import types
from apimas.modeling import utils
from apimas.modeling.cli.custom_types import (
    Email, Json, Credentials, Date, DateTime)
from apimas.modeling.clients import ApimasClientAdapter
from apimas.modeling.core import documents as doc, exceptions as ex
from apimas.modeling.adapters.cookbooks import NaiveAdapter, SKIP


def to_option(name):
    return '--' + name


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


@click.group(name='apimas')
def base_group():
    pass


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


class ApimasCliAdapter(NaiveAdapter):
    ADAPTER_CONF = 'cli_conf'

    # Map specification predications to click-known types.
    TYPE_MAPPING = {
        'integer': types.IntParamType,
        'serial': types.IntParamType,
        'string': types.StringParamType,
        'email': Email,
        'boolean': types.BoolParamType,
        'biginteger': types.IntParamType,
        'float': types.FloatParamType,
        'date': Date,
        'datetime': DateTime,
        'ref': types.StringParamType,
        'structarray': Json,
        'file': functools.partial(types.File, mode='rb')
    }

    # Map actions to commands.
    COMMANDS = {
        'list': ListCommand,
        'create': CreateCommand,
        'update': UpdateCommand,
        'delete': DeleleCommand,
        'retrieve': RetrieveCommand,
    }

    OPTION_CONSTRUCTORS = {
        'list': lambda x, y: click.option(
            to_option(x),
            **{k: v for k, v in y.iteritems() if k != 'required'}),
        'create': lambda x, y: click.option(to_option(x), **y),
        # Note that command of update, it performs a `PATCH` request instead
        # `PUT`. Thus, user does not need to specify all fields for the action
        # but only the fields which they actually want to update.
        'update': lambda x, y: click.option(
            to_option(x),
            **{k: v for k, v in y.iteritems() if k != 'required'}),
        'delete': None,
        'retrieve': lambda x, y: click.option(
            to_option(x),
            **{k: v for k, v in y.iteritems() if k != 'required'})
    }

    WRITE_ACTIONS = {
        'create',
        'update',
    }

    READ_ACTIONS = {
        'list',
        'retrieve',
    }

    # List actions performed on specific resources.
    RESOURCE_ACTIONS = {
        'retrieve',
        'update',
        'delete',
    }

    CRITICAL_ACTIONS = {'delete'}

    EXTRA_PREDICATES = [
        '.cli_option',
        '.cli_commands',
        '.cli_auth',
        '.auth_format'
    ]

    SKIP_FIELDS = {'.identity'}

    PREDICATES = list(NaiveAdapter.PREDICATES) + EXTRA_PREDICATES

    def __init__(self, clients):
        self.clients = clients
        self.struct_map = {}
        self.commands = []

    def get_commands(self):
        """
        Get a list commands
        """
        return self.commands

    def option_allowed(self, action, spec, option_constructor):
        """
        Check if an option should be attached to a specific command.

        There are some cases that an option cannot be applied. For instance,
        if a command is associated with write operations, e.g. create, update,
        there should not be options for `readonly` fields.

        Similarly, if a command corresponds to read operations,
        options corresponding to `indexable` fields should should be created.
        """
        if option_constructor is None:
            return False
        if action in self.WRITE_ACTIONS and '.readonly' in spec:
            return False
        if action in self.READ_ACTIONS and '.indexable' not in spec:
            return False
        return True

    def _add_format_option(self, command, action):
        """
        Add format option.

        This option defines the format type of the command output. This
        option is attached only on `ListCommand` and `RetrieveCommand`.

        :param command: Command instance.
        :param action: Action type, e.g. 'list', 'retrieve', etc.
        """
        if action in self.READ_ACTIONS:
            return click.option(
                '--format', type=click.Choice(['json', 'table']),
                default='json')(command)

    def construct_cli_auth(self, instance, spec, loc, context):
        """
        Constructor of `.cli_auth` predicate.

        It adds an additional option to all commands in order to specify
        credentials to interact with the API.

        There are multiple authentication model that can be supported according
        to the specification. However, credentials must be stored in a
        configuration file of specific format (`JSON` and `YAML` are supported
        at the momment).
        """
        if self.ADAPTER_CONF not in instance:
            raise doc.DeferConstructor
        auth_format = doc.doc_get(spec, ('.auth_format', 'format'))
        auth_modes = self.get_structural_elements(spec)
        auth_schema = {}
        for auth_mode in auth_modes:
            schema = doc.doc_get(spec, (auth_mode,))
            auth_schema[auth_mode] = schema
        commands = doc.doc_get(instance, (self.ADAPTER_CONF, 'actions'))
        assert commands, (
            'Loc: %s, commands have not been constructed yet.' % (str(loc)))
        credential_option = click.option(
            '--credentials', required=True, type=Credentials(
                schema=auth_schema, file_type=auth_format))
        for command in commands:
            credential_option(command)
        return instance

    def construct_auth_format(self, instance, spec, loc, context):
        self.init_adapter_conf(instance, initial={'format': spec})
        return instance

    def construct_cli_commands(self, instance, spec, loc, context):
        """
        Constructor for '.cli_commands' predicate.

        Gets all commands corresponding to actions and attaches the
        appropriate options to them based on field schema.
        """
        parent_name = context.get('parent_name')
        instance = self.init_adapter_conf(instance, initial={'actions': set()})
        commands = doc.doc_get(instance, ('actions', self.ADAPTER_CONF)) or {}
        for action, command in commands.iteritems():
            command = self.construct_command(
                instance, parent_name, spec, loc, action, command)
            instance[self.ADAPTER_CONF]['actions'].add(command)
        return instance

    def construct_action(self, instance, spec, loc, context, action):
        """
        Construct a command based on a specific actions, e.g. list,
        create, etc.
        """
        assert len(loc) == 4
        self.init_adapter_conf(instance)
        command = self.COMMANDS[action](self.clients.get(loc[-3]))
        if action in self.RESOURCE_ACTIONS:
            command = click.argument('resource_id')(command)
        if action in self.CRITICAL_ACTIONS:
            option = click.option(
                '--yes', is_flag=True, callback=abort_if_false,
                expose_value=False,
                prompt='Are you sure you want to perform this action?')
            command = option(command)
        self._add_format_option(command, action)
        instance[self.ADAPTER_CONF][action] = command
        return instance

    def construct_command(self, instance, command_name, spec, loc, action,
                          command):
        """
        Construct command's options for a specific collection according to the
        `APIMAS` specification.
        """
        field_schema = doc.doc_get(instance, ('*',))
        for field_name, spec in field_schema.iteritems():
            if spec == SKIP:
                continue
            for option_name, params in spec.get(self.ADAPTER_CONF).iteritems():
                option_constructor = self.OPTION_CONSTRUCTORS[action]
                if not self.option_allowed(action, spec, option_constructor):
                    continue
                command = option_constructor(option_name, params)(command)
                path = (field_name,) if '.struct' not in spec\
                    else self.struct_map[option_name]
                command.register_option_mapping(
                    option_name.replace('-', '_'), path)
        return base_group.command(name=loc[-2] + '-' + action)(command)

    def construct_list(self, instance, spec, loc, context):
        """
        Constructor for '.list' predicate.

        This constructs a `ListCommand` according to the spec.
        """
        return self.construct_action(instance, spec, loc, context, 'list')

    def construct_create(self, instance, spec, loc, context):
        """
        Constructor for '.create' predicate.

        This constructs a `CreateCommand` according to the spec.
        """
        return self.construct_action(
            instance, spec, loc, context, 'create')

    def construct_update(self, instance, spec, loc, context):
        """
        Constructor for '.update' predicate.

        This constructs a `UpdateCommand` according to the spec.
        """
        return self.construct_action(
            instance, spec, loc, context, 'update')

    def construct_delete(self, instance, spec, loc, context):
        """
        Constructor for '.delete' predicate.

        This constructs a `DeleteCommand` according to the spec.
        """
        return self.construct_action(instance, spec, loc, context, 'delete')

    def construct_retrieve(self, instance, spec, loc, context):
        """
        Constructor for '.retrieve' predicate.

        This constructs a `RetrieveCommand` according to the spec.
        """
        return self.construct_action(instance, spec, loc, context, 'retrieve')

    def construct_struct_option(self, instance, parent_name, spec, loc,
                                option_name):
        """
        Constructor for `.struct` predicate.

        This field corresponds to a python `dict` with all options and their
        keyword parameters associated with this field.

        A struct is consisted of all options of its field schema.
        Example:

        A struct named 'cart' which incorporates fields `id` and `products`
        corresponds to the following options:

        * --cart-id
        * --cart-products
        """
        option_kwargs = {}
        self.init_adapter_conf(instance)
        for _, schema in doc.doc_get(
                instance, ('.struct',)).iteritems():
            if schema == SKIP:
                continue
            for nested, params in schema.get(self.ADAPTER_CONF).iteritems():
                option_kwargs.update({option_name + '-' + nested: params})
                self.struct_map[option_name + '-' + nested] = (
                    parent_name,) + self.struct_map.get(nested, (nested,))
        instance[self.ADAPTER_CONF].update(option_kwargs)
        return instance

    def construct_option_type(self, instance, spec, loc, context,
                              predicate_type):
        constructors = {
            '.date': self._add_date_params,
            '.datetime': self._add_date_params,
        }

        def default(instance, spec, loc, context):
            return {}

        if predicate_type in self.SKIP_FIELDS:
            return None

        kwargs = constructors.get(predicate_type, default)(
            instance, spec, loc, context)
        option_type = self.TYPE_MAPPING[predicate_type[1:]]
        return option_type(**kwargs)

    def construct_identity(self, instance, spec, loc, context):
        instance = SKIP
        return instance

    def construct_cli_option(self, instance, spec, loc, context):
        """
        Constructor for '.cli_option' predicate.

        It constructs a dictionary keyed by option name which contains
        all required keyword arguments for `click.option()` constructor.
        """
        parent_name = context.get('parent_name')
        extra_params = {'.ref': self._add_ref_params}
        if instance == SKIP:
            return instance
        predicate_type = self.extract_type(instance)
        option_name = doc.doc_get(
            spec, ('option_name',)) or parent_name
        if predicate_type == '.struct':
            return self.construct_struct_option(instance, parent_name, spec,
                                                loc, option_name)
        instance = self.init_adapter_conf(instance, initial={option_name: {}})
        kwargs = {'type': self.construct_option_type(
            instance, spec, loc, context, predicate_type)}
        extra = extra_params.get(predicate_type)
        if extra:
            kwargs.update(extra(instance, spec, loc, context))
        if '.required' in instance:
            kwargs.update({'required': True})
        instance[self.ADAPTER_CONF][option_name] = kwargs
        return instance

    def _add_date_params(self, instance, spec, loc, context):
        return {'date_format': spec.get('format', None)}

    def _add_ref_params(self, instance, spec, loc, context):
        many = doc.doc_get(instance, ('.ref', 'many'))
        return {'multiple': True} if many else {}

    def construct_struct(self, instance, spec, loc, context):
        return instance

    def construct_type(self, instance, spec, loc, context, field_type):
        return instance

    def construct_property(self, instance, spec, loc, context, property_name):
        """
        Constuctor for `.required` predicate.
        """
        return instance


def main():
    data = utils.load_config()
    root_url = data['root']
    spec = data['spec']
    client_gen = ApimasClientAdapter(root_url)
    client_gen.construct(spec)
    client_gen.apply()
    cli = ApimasCliAdapter(client_gen.get_clients())
    cli.construct(spec)
    base_group()


if __name__ == '__main__':
    main()

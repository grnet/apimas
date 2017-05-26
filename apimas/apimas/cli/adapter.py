import functools
import click
from click import types
from apimas import documents as doc
from apimas.errors import InvalidSpec, NotFound
from apimas.cli import (ListCommand, RetrieveCommand, CreateCommand,
                        UpdateCommand, DeleleCommand, abort_if_false)
from apimas.cli.custom_types import (
    Email, Json, Credentials, Date, DateTime)
from apimas.adapters.cookbooks import NaiveAdapter, SKIP


def to_option(name):
    return '--' + name


@click.group(name='group')
def base_command():
    pass


class ApimasCliAdapter(NaiveAdapter):
    ADAPTER_CONF = 'cli_conf'

    # Map specification predications to click-known types.
    TYPE_MAPPING = {
        'integer': types.IntParamType,
        'serial': types.IntParamType,
        'string': types.StringParamType,
        'text': types.StringParamType,
        'choices': types.Choice,
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

    EXTRA_PARAMS = {
        '.choices': {
            'allowed': {
                'default': [],
                'map': 'choices',
            },
        },
        '.date': {
            'format': {
                'default': ['%Y-%m-%d'],
                'map': 'date_formats',
            }
        },
        '.datetime': {
            'format': {
                'default': ['%Y-%m-%dT%H:%M:%S'],
                'map': 'date_formats',
            }
        }
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
    ]

    SKIP_FIELDS = {'.identity'}

    PREDICATES = list(NaiveAdapter.PREDICATES) + EXTRA_PREDICATES

    def __init__(self, clients):
        self.clients = clients
        self._struct_map = {}
        self.commands = {}
        self.endpoint_groups = {}

    def get_commands(self):
        """ Get a list of commands for all collections. """
        return self.commands

    def get_base_command(self):
        return base_command

    def get_collection_commands(self, endpoint, collection):
        """
        Get all commands to interact with a specific collection which belongs
        to a specific endpoint.

        :raises: NotFound if commands are not found for the selected
        collection.
        """
        collection_name = endpoint + '/' + collection
        if collection_name not in self.commands:
            raise NotFound(
                'Commands not found for collection {!r}'.format(
                    collection_name))
        return self.commands[collection_name]

    def get_or_create_endpoint_group(self, endpoint):
        """
        Gets a group of commands for a specific endpoint.

        If a group does not exist for a specific endpoint, then it is created
        and it's returned.

        :param endpoint: Name of the node which is an endpoint.
        :returns: A group of commands. Each command corresponds to an action
        performed on a collection which belongs to the endpoint.
        """
        def group():
            pass

        if endpoint not in self.endpoint_groups:
            base_cmd = self.get_base_command()
            endpoint_group = base_cmd.group(name=endpoint)(group)
            self.endpoint_groups[endpoint] = endpoint_group
            return endpoint_group
        return self.endpoint_groups[endpoint]

    def option_allowed(self, action, spec, option_constructor):
        """
        Check if an option should be attached to a specific command.

        There are some cases that an option cannot be applied. For instance,
        if a command is associated with write operations, e.g. create, update,
        there should not be options for `readonly` fields.
        """
        if option_constructor is None:
            return False
        if action in self.WRITE_ACTIONS and '.readonly' in spec:
            return False
        if action in self.READ_ACTIONS:
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

    def construct_cli_auth(self, context):
        """
        Constructor of `.cli_auth` predicate.

        It adds an additional option to all commands in order to specify
        credentials to interact with the API.

        There are multiple authentication model that can be supported according
        to the specification. However, credentials must be stored in a
        configuration file of specific format (`JSON` and `YAML` are supported
        at the momment).
        """
        if self.ADAPTER_CONF not in context.instance:
            raise doc.DeferConstructor
        auth_format = context.spec.get('format')
        if auth_format is None:
            raise InvalidSpec('`format` parameter is missing',
                              loc=context.loc)
        auth_schema = context.spec.get('schema')
        if auth_schema is None:
            raise InvalidSpec('`schema` parameter is missing',
                              loc=context.loc)
        commands = doc.doc_get(
            context.instance, (self.ADAPTER_CONF, '.actions'))
        assert commands, (
            'Loc: {!r}, commands have not been constructed yet.'.format(
                str(context.loc)))
        credential_option = click.option(
            '--credentials', required=True, type=Credentials(
                schema=auth_schema, file_type=auth_format))
        for command in commands:
            credential_option(command)
        return context.instance

    def construct_cli_commands(self, context):
        """
        Constructor for '.cli_commands' predicate.

        Gets all commands corresponding to actions and attaches the
        appropriate options to them based on field schema.
        """
        parent_name = context.parent_name
        instance = self.init_adapter_conf(
            context.instance, initial={'.actions': set()})
        commands = doc.doc_get(instance, ('.actions', self.ADAPTER_CONF)) or {}
        collection_name = context.loc[0] + '/' + parent_name
        self.commands[collection_name] = []
        for action, command in commands.iteritems():
            command = self.construct_command(
                instance, parent_name, context.spec, context.loc, action,
                command)
            self.commands[collection_name].append(command)
            instance[self.ADAPTER_CONF]['.actions'].add(command)
        return instance

    def construct_action(self, context, action):
        """
        Construct a command based on a specific actions, e.g. list,
        create, etc.
        """
        assert len(context.loc) == 4
        self.init_adapter_conf(context.instance)
        collection = context.loc[0] + '/' + context.loc[-3]
        command = self.COMMANDS[action](self.clients.get(collection))
        if action in self.RESOURCE_ACTIONS:
            command = click.argument('resource_id')(command)
        if action in self.CRITICAL_ACTIONS:
            option = click.option(
                '--yes', is_flag=True, callback=abort_if_false,
                expose_value=False,
                prompt='Are you sure you want to perform this action?')
            command = option(command)
        self._add_format_option(command, action)
        context.instance[self.ADAPTER_CONF][action] = command
        return context.instance

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
            adapter_conf = spec.get(self.ADAPTER_CONF)
            # In case there is not option specified for this field,
            # just skip it.
            if adapter_conf is None:
                continue
            for option_name, params in spec.get(self.ADAPTER_CONF).iteritems():
                option_constructor = self.OPTION_CONSTRUCTORS[action]
                if not self.option_allowed(action, spec, option_constructor):
                    continue
                command = option_constructor(option_name, params)(command)
                path = (field_name,) if '.struct=' not in spec\
                    else self._struct_map[option_name]
                command.register_option_mapping(
                    option_name.replace('-', '_'), path)
        endpoint_group = self.get_or_create_endpoint_group(loc[0])
        return endpoint_group.command(loc[-2] + '-' + action)(command)

    def construct_list(self, context):
        """
        Constructor for '.list' predicate.

        This constructs a `ListCommand` according to the spec.
        """
        return self.construct_action(context, 'list')

    def construct_create(self, context):
        """
        Constructor for '.create' predicate.

        This constructs a `CreateCommand` according to the spec.
        """
        return self.construct_action(
            context, 'create')

    def construct_update(self, context):
        """
        Constructor for '.update' predicate.

        This constructs a `UpdateCommand` according to the spec.
        """
        return self.construct_action(
            context, 'update')

    def construct_delete(self, context):
        """
        Constructor for '.delete' predicate.

        This constructs a `DeleteCommand` according to the spec.
        """
        return self.construct_action(context, 'delete')

    def construct_retrieve(self, context):
        """
        Constructor for '.retrieve' predicate.

        This constructs a `RetrieveCommand` according to the spec.
        """
        return self.construct_action(context, 'retrieve')

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
                instance, ('.struct=',)).iteritems():
            if schema == SKIP:
                continue
            for nested, params in schema.get(self.ADAPTER_CONF).iteritems():
                option_kwargs.update({option_name + '-' + nested: params})
                self._struct_map[option_name + '-' + nested] = (
                    parent_name,) + self._struct_map.get(nested, (nested,))
        instance[self.ADAPTER_CONF].update(option_kwargs)
        return instance

    def construct_option_type(self, context,
                              predicate_type):
        if predicate_type in self.SKIP_FIELDS:
            return None

        extra_kwargs = self.get_extra_params(context.instance, predicate_type)
        option_type = self.TYPE_MAPPING[predicate_type[1:]]
        return option_type(**extra_kwargs)

    def construct_identity(self, context):
        instance = SKIP
        return instance

    def construct_cli_option(self, context):
        """
        Constructor for '.cli_option' predicate.

        It constructs a dictionary keyed by option name which contains
        all required keyword arguments for `click.option()` constructor.
        """
        parent_name = context.parent_name
        instance = context.instance
        spec = context.spec
        loc = context.loc
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
            context, predicate_type)}
        if predicate_type == '.ref':
            kwargs.update(self._add_ref_params(context))
        if '.required' in instance:
            kwargs.update({'required': True})
        instance[self.ADAPTER_CONF][option_name] = kwargs
        return instance

    def _add_ref_params(self, context):
        many = doc.doc_get(context.instance, ('.ref', 'many'))
        return {'multiple': True} if many else {}

    def construct_struct(self, context):
        return context.instance

    def construct_type(self, context, field_type):
        return context.instance

    def construct_property(self, context, property_name):
        """
        Constuctor for `.required` predicate.
        """
        return context.instance

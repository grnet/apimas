import unittest
import mock
from apimas import documents as doc, exceptions as ex
from apimas.testing.helpers import create_mock_object
from apimas.cli.adapter import ApimasCliAdapter
from apimas.adapters.cookbooks import SKIP


class TestCliAdapter(unittest.TestCase):
    adapter_conf = ApimasCliAdapter.ADAPTER_CONF

    def test_get_collection_commands(self):
        mock_adapter = create_mock_object(ApimasCliAdapter,
                                          ['get_collection_commands'])
        mock_adapter.commands = {}
        self.assertRaises(ex.ApimasException,
                          mock_adapter.get_collection_commands,
                          mock_adapter, endpoint='api',
                          collection='collection')
        mock_commands = {'api/collection': 'value'}
        mock_adapter.commands = mock_commands
        value = mock_adapter.get_collection_commands(
            mock_adapter, endpoint='api', collection='collection')
        self.assertEquals(value, mock_commands['api/collection'])

    def test_get_or_create_endpoint_group(self):
        mock_cli = create_mock_object(ApimasCliAdapter,
                                      ['get_or_create_endpoint_group'])
        mock_cli.endpoint_groups = {}
        mock_cmd = mock.Mock()
        mock_cli.get_base_command.return_value = mock_cmd
        mock_command = mock.Mock()
        mock_cmd.group.return_value = mock_command

        # Case A: Endpoint group already exists.
        mock_cli.endpoint_groups = {'foo': 'test'}
        endpoint_group = mock_cli.get_or_create_endpoint_group(
            mock_cli, 'foo')
        self.assertEqual(len(mock_cli.endpoint_groups), 1)
        self.assertEqual(mock_cli.endpoint_groups['foo'], endpoint_group)
        mock_cmd.group.assert_not_called
        mock_command.assert_not_called

        # Case B: Endpoint group does not exist and we create it.
        mock_cli.endpoint_groups = {}
        endpoint_group = mock_cli.get_or_create_endpoint_group(
            mock_cli, 'foo')
        self.assertTrue(isinstance(endpoint_group, mock.Mock))
        mock_cmd.group.assert_called_once_with(name='foo')
        mock_command.assert_called_once
        self.assertEqual(len(mock_cli.endpoint_groups), 1)
        self.assertEqual(mock_cli.endpoint_groups['foo'], endpoint_group)

    def test_option_allowed(self):
        cli_adapter = ApimasCliAdapter(clients={})
        self.assertFalse(cli_adapter.option_allowed(
            action=None, spec={}, option_constructor=None))

        actions = {'foo', 'bar'}
        cli_adapter.WRITE_ACTIONS = actions
        spec = {'.readonly'}
        self.assertFalse(cli_adapter.option_allowed(
            action='foo', spec=spec, option_constructor='bar'))

        cli_adapter.READ_ACTIONS = actions
        self.assertFalse(cli_adapter.option_allowed(
            action='foo', spec={}, option_constructor='bar'))

    @mock.patch('click.option')
    def test_add_format_option(self, mock_option):
        cli_adapter = ApimasCliAdapter(clients={})
        actions = set()
        cli_adapter.READ_ACTIONS = actions

        cli_adapter._add_format_option(command='bar', action='foo')
        mock_option.assert_not_called

        actions = {'foo', 'bar'}
        cli_adapter.READ_ACTIONS = actions
        cli_adapter._add_format_option(command='bar', action='foo')
        mock_option.assert_called_once

    @mock.patch('apimas.cli.adapter.Credentials')
    @mock.patch('click.option')
    def test_construct_cli_auth(self, mock_option, mock_credentials):
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_cli_auth', 'ADAPTER_CONF'],
            ismagic=True)
        self.assertRaises(doc.DeferConstructor, mock_cli.construct_cli_auth,
                          mock_cli, {}, {}, (), {})

        mock_option_ret = mock.MagicMock()
        mock_option.return_value = mock_option_ret
        mock_a = mock.MagicMock()
        mock_b = mock.MagicMock()
        mock_c = mock.MagicMock()
        mock_commands = {'.actions': [mock_a, mock_b, mock_c]}
        mock_instance = {self.adapter_conf: mock_commands}
        mock_schema = {
            'a': {'foo': {}},
            'b': {'bar': {}},
        }

        # Case A: Missing parameter 'format'.
        mock_spec = {'schema': mock_schema}
        self.assertRaises(ex.ApimasAdapterException,
                          mock_cli.construct_cli_auth, mock_cli, mock_instance,
                          mock_spec, (), {})

        # Case B: Missing parameter 'schema'.
        mock_spec = {'format': mock_schema}
        self.assertRaises(ex.ApimasAdapterException,
                          mock_cli.construct_cli_auth, mock_cli, mock_instance,
                          mock_spec, (), {})

        # Case C: Construct --credentials option for every command.
        mock_spec = {'format': 'mock_format', 'schema': mock_schema}
        mock_cli.construct_cli_auth(
            mock_cli, mock_instance, mock_spec, (), {})
        mock_option.assert_called_once
        self.assertEqual(mock_option_ret.call_count, 3)
        mock_credentials.assert_called_once_with(
            schema=mock_schema, file_type='mock_format')
        mock_option.assert_called_once
        mock_option_ret.assert_any_call(mock_a)
        mock_option_ret.assert_any_call(mock_b)
        mock_option_ret.assert_any_call(mock_c)

    def test_construct_cli_commands(self):
        mock_loc = ('foo', 'bar', '.cli_commands')
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_cli_commands', 'ADAPTER_CONF'])
        mock_cli.commands = {}
        mock_instance = {
            self.adapter_conf: {'.actions': set()}
        }
        mock_context = {'parent_name': 'foo'}
        mock_cli.init_adapter_conf.return_value = mock_instance
        instance = mock_cli.construct_cli_commands(
            mock_cli, instance={}, spec={}, loc=mock_loc, context=mock_context)
        self.assertEqual(instance, mock_instance)
        mock_cli.init_adapter_conf.assert_called_once_with(
            {}, initial={'.actions': set()})

        initial_instance = {
            '.actions': {
                self.adapter_conf: {
                    'a': 'foo',
                    'b': 'bar',
                }
            }
        }

        instance_and_conf = dict(mock_instance, **initial_instance)
        mock_cli.init_adapter_conf.return_value = instance_and_conf
        mock_cli.construct_command.return_value = 'foo_bar'
        instance = mock_cli.construct_cli_commands(
            mock_cli, instance=initial_instance, spec={}, loc=mock_loc,
            context=mock_context)
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_cli.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 1)
        self.assertEqual(instance_conf['.actions'], {'foo_bar'})

        mock_cli.init_adapter_conf.assert_called_with(
            initial_instance, initial={'.actions': set()})
        self.assertEqual(mock_cli.construct_command.call_count, 2)
        mock_cli.construct_command.assert_any_call(
            instance_and_conf, 'foo', {}, mock_loc, 'a', 'foo')
        mock_cli.construct_command.assert_any_call(
            instance_and_conf, 'foo', {}, mock_loc, 'b', 'bar')

    @mock.patch('click.option')
    @mock.patch('click.argument')
    def test_construct_action(self, mock_argument, mock_option):
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_action', 'ADAPTER_CONF'])
        mock_cli.clients = {}
        actions = {'foo'}
        mock_loc = ('foo', 'bar', '.actions', 'action')
        mock_cli.CRITICAL_ACTIONS = actions
        mock_cli.RESOURCE_ACTIONS = actions
        mock_command = mock.MagicMock()
        mock_command.return_value = 'foo_command'
        mock_command2 = mock.MagicMock()
        mock_command2.return_value = 'bar_command'

        commands = {'foo': mock_command, 'bar': mock_command2}
        mock_cli.COMMANDS = commands

        mock_instance = {self.adapter_conf: {}}

        instance = mock_cli.construct_action(
            mock_cli, instance=mock_instance, spec={}, loc=mock_loc,
            context={}, action='bar')
        self.assertEqual(len(instance), 1)
        instance_conf = instance.get(mock_cli.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 1)
        self.assertEqual(instance_conf['bar'], 'bar_command')
        mock_command2.assert_called_once
        mock_command.assert_not_called
        mock_argument.assert_not_called
        mock_option.assert_not_called

        mock_a = mock.MagicMock()
        mock_a.return_value = 'argument_ret'
        mock_b = mock.MagicMock()
        mock_b.return_value = 'option_ret'
        mock_argument.return_value = mock_a
        mock_option.return_value = mock_b

        instance = mock_cli.construct_action(
            mock_cli, instance=mock_instance, spec={}, loc=mock_loc,
            context={}, action='foo')
        self.assertEqual(len(instance), 1)
        instance_conf = instance.get(mock_cli.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 2)
        self.assertEqual(instance_conf['foo'], 'option_ret')

        mock_argument.assert_called_once
        mock_a.assert_called_with('foo_command')

        mock_option.assert_called_once
        mock_b.assert_called_once_with('argument_ret')

    def test_construct_command(self):
        mock_cli = create_mock_object(
            ApimasCliAdapter,
            ['construct_command', 'ADAPTER_CONF', 'OPTION_CONSTRUCTORS'])

        mock_loc = ('foo', 'bar')
        mock_instance = {
            '*': {
                'foo': {
                    self.adapter_conf: {
                        'foo_option': {
                            'required': True
                        }
                    }
                },
                'bar': {
                    self.adapter_conf: {
                        'bar_option': {
                            'required': True
                        }
                    }
                },
                'another': SKIP,
            }
        }

        command_name = 'foo'
        mock_obj = mock.MagicMock()
        mock_obj.return_value = 'test'
        mock_group = mock.Mock()
        mock_cli.get_or_create_endpoint_group.return_value = mock_group
        mock_group.command.return_value = mock_obj
        for action in ['create', 'list', 'update', 'retrieve']:
            mock_cli.option_allowed.return_value = action != 'delete'
            with mock.patch('click.option') as mock_option:
                command = mock_cli.construct_command(
                    mock_cli, instance=mock_instance,
                    command_name=command_name, spec={}, loc=mock_loc,
                    action=action, command='foo')
                self.assertEqual(command, 'test')
                if action == 'create':
                    self.assertEqual(mock_option.call_count, 2)
                    mock_option.assert_any_call(
                        '--bar_option', required=True)
                    mock_option.assert_any_call(
                        '--foo_option', required=True)
                elif action == 'delete':
                    mock_option.assert_not_called
                else:
                    self.assertEqual(mock_option.call_count, 2)
                    mock_option.assert_any_call('--bar_option')
                    mock_option.assert_any_call('--foo_option')

    def test_construct_struct_option(self):
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_struct_option', 'ADAPTER_CONF'])
        mock_cli._struct_map = {}
        mock_loc = ('foo', 'bar')

        mock_instance = {
            '.struct': {
                'foo': {
                    self.adapter_conf: {
                        'foo_option': {
                            'a': {},
                        }
                    }
                },
                'bar': SKIP,
            },
            self.adapter_conf: {},
        }
        parent_name = 'foo'
        instance = mock_cli.construct_struct_option(
            mock_cli, instance=mock_instance, parent_name=parent_name, spec={},
            loc=mock_loc, option_name='test')
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_cli.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 1)
        self.assertEqual(instance_conf['test-foo_option'], {'a': {}})
        self.assertEqual(mock_cli._struct_map,
                         {'test-foo_option': ('foo', 'foo_option')})

    def test_construct_option_type(self):
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_option_type'])
        mock_cli.SKIP_FIELDS = {'foo'}
        mock_cli.get_extra_params.return_value = {'bar1': 'value_a',
                                                  'bar2': 'value_b'}
        mock_a = mock.Mock()
        mock_a.return_value = 'test'
        mock_b = mock.Mock()
        type_mapping = {
            'a': mock_a,
            'b': mock_b,
        }
        mock_cli.TYPE_MAPPING = type_mapping

        # Case A: A field which we skip.
        self.assertIsNone(mock_cli.construct_option_type(
            mock_cli, instance={}, spec={}, loc={}, context={},
            predicate_type='foo'))

        # Case B: A common field.
        option_type = mock_cli.construct_option_type(
            mock_cli, instance={}, spec={}, loc={}, context={},
            predicate_type='.a')
        self.assertEqual(option_type, 'test')
        mock_b.assert_not_called
        mock_a.assert_called_once_with(bar1='value_a',
                                       bar2='value_b')

    def test_construct_idenity(self):
        cli = ApimasCliAdapter({})
        self.assertEqual(cli.construct_identity(
            instance={}, spec={}, loc=(), context={}), SKIP)

    def test_construct_cli_option(self):
        context = {'parent_name': 'foo'}
        mock_loc = ('foo', 'bar', '*', 'field', 'type')
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_cli_option', 'ADAPTER_CONF'])
        mock_cli.construct_option_type.return_value = 'option type'

        self.assertEqual(mock_cli.construct_cli_option(
            mock_cli, instance=SKIP, spec={}, loc=mock_loc, context=context),
                         SKIP)
        mock_cli.extract_type.assert_not_called

        mock_cli.extract_type.return_value = '.struct'
        spec = {'option_name': 'my'}
        mock_cli.construct_struct_option.return_value = 'struct_option'
        instance = mock_cli.construct_cli_option(
            mock_cli, instance={}, spec=spec, loc=mock_loc, context=context)
        self.assertEqual(instance, 'struct_option')
        mock_cli.extract_type.assert_called_with({})
        mock_cli.construct_struct_option.assert_called_once_with(
            {}, 'foo', spec, mock_loc, 'my')

        mock_cli.extract_type.return_value = 'foo'
        mock_cli.init_adapter_conf.return_value = {
            self.adapter_conf: {'my': {}}}
        instance = mock_cli.construct_cli_option(
            mock_cli, instance={}, spec=spec, loc=mock_loc, context=context)
        self.assertEqual(instance[self.adapter_conf]['my'],
                         {'type': 'option type'})
        mock_cli.construct_option_type.assert_called_once

        mock_cli.init_adapter_conf.return_value = {
            self.adapter_conf: {'my': {}}, '.required': {}}
        instance = mock_cli.construct_cli_option(
            mock_cli, instance={}, spec=spec, loc=mock_loc, context=context)
        self.assertEqual(instance[self.adapter_conf]['my'],
                         {'type': 'option type', 'required': True})

import datetime
import unittest
import mock
from click.exceptions import BadParameter
from apimas.modeling.core import documents as doc
from apimas.modeling.tests.helpers import create_mock_object
from apimas.modeling.cli.custom_types import Json, Date, DateTime, Credentials
from apimas.modeling.cli.cli import ApimasCliAdapter, BaseCommand
from apimas.modeling.adapters.cookbooks import SKIP


class TestCustomTypes(unittest.TestCase):

    def test_json(self):
        value = '{"key": "value"}'
        json = Json()
        output = json.convert(value, '', '')
        self.assertTrue(isinstance(output, dict))
        self.assertEqual(len(output), 1)
        self.assertEqual(output['key'], 'value')

        value = 'invalid'
        self.assertRaises(BadParameter, json.convert, value, '', '')

    def test_datetime(self):
        value = '1985-11-12 13:14'
        date_format = '%Y-%m-%d %H:%M'
        datetime_obj = DateTime(date_format)
        output = datetime_obj.convert(value, '', '')
        self.assertTrue(isinstance(output, datetime.datetime))
        self.assertEqual(output.year, 1985)
        self.assertEqual(output.month, 11)
        self.assertEqual(output.day, 12)
        self.assertEqual(output.hour, 13)
        self.assertEqual(output.minute, 14)

        value = 'invalid'
        self.assertRaises(BadParameter, datetime_obj.convert, value, '', '')

    def test_date(self):
        value = '1985-11-12'
        date_format = '%Y-%m-%d'
        date_obj = Date(date_format)
        output = date_obj.convert(value, '', '')
        self.assertTrue(isinstance(output, datetime.date))
        self.assertEqual(output.year, 1985)
        self.assertEqual(output.month, 11)
        self.assertEqual(output.day, 12)

        value = 'invalid'
        self.assertRaises(BadParameter, date_obj.convert, value, '', '')


class TestCredentials(unittest.TestCase):
    credentials = {
        'a': {
            'foo': {},
        },
        'b': {
            'bar': {},
        }
    }

    def test_parse_credentials(self):
        schema = {'a': ['foo']}
        cred = Credentials(schema=schema)
        auth_type, auth_schema = cred.parse_credentials(self.credentials)
        self.assertEqual(auth_type, 'a')
        self.assertEqual(auth_schema, {'foo': {}})

        cred.schema = {'a': ['bar']}
        self.assertRaises(BadParameter, cred.parse_credentials,
                          self.credentials)

        cred.schema = {'c': ['foo']}
        self.assertRaises(BadParameter, cred.parse_credentials,
                          self.credentials)

        self.credentials['default'] = 'b'
        cred.schema = {'a': ['foo']}
        self.assertRaises(BadParameter, cred.parse_credentials,
                          self.credentials)

        cred.schema = {'b': ['bar']}
        auth_type, auth_schema = cred.parse_credentials(self.credentials)
        self.assertEqual(auth_type, 'b')
        self.assertEqual(auth_schema, {'bar': {}})

    @mock.patch('__builtin__.super')
    @mock.patch('apimas.modeling.cli.custom_types.Credentials.load_yaml')
    @mock.patch('apimas.modeling.cli.custom_types.Credentials.load_json')
    def test_convert(self, mock_json, mock_yaml, mock_super):
        mock_cred_obj = create_mock_object(
            Credentials, ['convert'], ismagic=True)
        mock_cred_obj.fail.side_effect = BadParameter('')
        mock_super.convert.return_value = None
        mock_json.return_value = self.credentials
        mock_yaml.return_value = self.credentials
        mock_cred_obj.load_json = mock_json
        mock_cred_obj.load_yaml = mock_yaml

        mock_cred_obj.file_type = 'ivalid'
        self.assertRaises(BadParameter, mock_cred_obj.convert,
                          mock_cred_obj, '', '', '')

        mocks = {
            'json': mock_json,
            'yaml': mock_yaml,
        }
        for k, v in mocks.iteritems():
            mock_cred_obj.file_type = k
            mock_cred_obj.parse_credentials.return_value = ('foo', 'bar')
            foo, bar = mock_cred_obj.convert(mock_cred_obj, '', '', '')
            self.assertEqual(foo, 'foo')
            self.assertEqual(bar, 'bar')
            mock_cred_obj.parse_credentials.assert_called_with(v.return_value)


class TestCliAdapter(unittest.TestCase):
    adapter_conf = ApimasCliAdapter.ADAPTER_CONF

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

        spec = {'.indexable'}
        self.assertTrue(cli_adapter.option_allowed(
            action='foo', spec=spec, option_constructor='bar'))

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

    @mock.patch('apimas.modeling.cli.cli.Credentials')
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
        mock_commands = {
            'actions': [mock_a, mock_b, mock_c]
        }
        mock_instance = {self.adapter_conf: mock_commands}
        mock_schema = {
            'a': {'foo': {}},
            'b': {'bar': {}},
        }
        mock_spec = {'.auth_format': {'format': 'mock_format'}}
        mock_spec.update(mock_schema)
        mock_cli.get_structural_elements.return_value = ['a', 'b']
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
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_cli_commands', 'ADAPTER_CONF'])
        mock_instance = {
            self.adapter_conf: {'actions': set()}
        }
        mock_cli.init_adapter_conf.return_value = mock_instance
        instance = mock_cli.construct_cli_commands(
            mock_cli, instance={}, spec={}, loc=(), context={})
        self.assertEqual(instance, mock_instance)
        mock_cli.init_adapter_conf.assert_called_once_with(
            {}, initial={'actions': set()})

        initial_instance = {
            'actions': {
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
            mock_cli, instance=initial_instance, spec={}, loc=(), context={})
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_cli.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 1)
        self.assertEqual(instance_conf['actions'], {'foo_bar'})

        mock_cli.init_adapter_conf.assert_called_with(
            initial_instance, initial={'actions': set()})
        self.assertEqual(mock_cli.construct_command.call_count, 2)
        mock_cli.construct_command.assert_any_call(
            instance_and_conf, {}, (), 'a', 'foo')
        mock_cli.construct_command.assert_any_call(
            instance_and_conf, {}, (), 'b', 'bar')

    @mock.patch('click.option')
    @mock.patch('click.argument')
    def test_construct_action(self, mock_argument, mock_option):
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_action', 'ADAPTER_CONF'])
        mock_cli.clients = {}
        actions = {'foo'}
        mock_loc = ('foo', 'bar', 'actions', 'action')
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

    @mock.patch('apimas.modeling.cli.cli.base_group')
    def test_construct_command(self, mock_group):
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

        mock_obj = mock.MagicMock()
        mock_obj.return_value = 'test'
        mock_group.command.return_value = mock_obj
        for action in ['create', 'list', 'update', 'retrieve']:
            mock_cli.option_allowed.return_value = action != 'delete'
            with mock.patch('click.option') as mock_option:
                command = mock_cli.construct_command(
                    mock_cli, instance=mock_instance, spec={}, loc=mock_loc,
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
        mock_cli.struct_map = {}
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
        instance = mock_cli.construct_struct_option(
            mock_cli, instance=mock_instance, spec={}, loc=mock_loc,
            option_name='test')
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_cli.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 1)
        self.assertEqual(instance_conf['test-foo_option'], {'a': {}})
        self.assertEqual(mock_cli.struct_map,
                         {'test-foo_option': ('foo', 'foo_option')})

    def test_contruct_option_type(self):
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_option_type'])
        mock_cli.SKIP_FIELDS = {'foo'}
        self.assertIsNone(mock_cli.construct_option_type(
            mock_cli, instance={}, spec={}, loc={}, context={},
            predicate_type='foo'))

        mock_a = mock.Mock()
        mock_a.return_value = 'test'
        mock_b = mock.Mock()
        type_mapping = {
            'a': mock_a,
            'b': mock_b,
        }
        mock_cli.TYPE_MAPPING = type_mapping
        option_type = mock_cli.construct_option_type(
            mock_cli, instance={}, spec={}, loc={}, context={},
            predicate_type='.a')
        self.assertEqual(option_type, 'test')
        mock_b.assert_not_called
        mock_a.assert_called_once_with()

    def test_construct_idenity(self):
        cli = ApimasCliAdapter({})
        self.assertEqual(cli.construct_identity(
            instance={}, spec={}, loc=(), context={}), SKIP)

    def test_construct_cli_option(self):
        mock_loc = ('foo', 'bar', '*', 'field', 'type')
        mock_cli = create_mock_object(
            ApimasCliAdapter, ['construct_cli_option', 'ADAPTER_CONF'])
        mock_cli.construct_option_type.return_value = 'option type'

        self.assertEqual(mock_cli.construct_cli_option(
            mock_cli, instance=SKIP, spec={}, loc=mock_loc, context={}), SKIP)
        mock_cli.extract_type.assert_not_called

        mock_cli.extract_type.return_value = '.struct'
        spec = {'option_name': 'my'}
        mock_cli.construct_struct_option.return_value = 'struct_option'
        instance = mock_cli.construct_cli_option(
            mock_cli, instance={}, spec=spec, loc=mock_loc, context={})
        self.assertEqual(instance, 'struct_option')
        mock_cli.extract_type.assert_called_with({})
        mock_cli.construct_struct_option.assert_called_once_with(
            {}, spec, mock_loc, 'my')

        mock_cli.extract_type.return_value = 'foo'
        mock_cli.init_adapter_conf.return_value = {
            self.adapter_conf: {'my': {}}}
        instance = mock_cli.construct_cli_option(
            mock_cli, instance={}, spec=spec, loc=mock_loc, context={})
        self.assertEqual(instance[self.adapter_conf]['my'],
                         {'type': 'option type'})
        mock_cli.construct_option_type.assert_called_once

        mock_cli.init_adapter_conf.return_value = {
            self.adapter_conf: {'my': {}}, '.required': {}}
        instance = mock_cli.construct_cli_option(
            mock_cli, instance={}, spec=spec, loc=mock_loc, context={})
        self.assertEqual(instance[self.adapter_conf]['my'],
                         {'type': 'option type', 'required': True})


class TestCommands(unittest.TestCase):

    def test_options_to_data(self):
        command = BaseCommand(client=None)
        command.option_mapping = {
            'bar': ['another'],
            'foo-bar-test': ['foo', 'bar-test']
        }

        option_values = {
            'bar': 'value',
            'foo-bar-test': (1, 2)
        }
        data = command.options_to_data(option_values)
        output = {
            'another': 'value',
            'foo': {
                'bar-test': [1, 2],
            }
        }
        self.assertEqual(data, output)

    def test_add_credentials(self):
        mock_client = mock.Mock()
        command = BaseCommand(client=mock_client)
        command.add_credentials({})
        mock_client.set_credentials.assert_not_called

        command.add_credentials({'credentials': ('foo', {'bar': {}})})
        mock_client.set_credentials.assert_called_once_with(
            'foo', **{'bar': {}})

    @mock.patch('tabulate.tabulate')
    def test_format_response(self, mock_tabulate):
        command = BaseCommand(client=None)
        with mock.patch('click.echo') as mock_echo:
            command.format_response(data={'foo': 'bar'}, format_type='json')
            mock_echo.assert_called_once_with('{\n  "foo": "bar"\n}')
            mock_tabulate.assert_not_called

        with mock.patch('click.echo') as mock_echo:
            mock_tabulate.return_value = 'test'
            command.format_response(data={'foo': 'bar'}, format_type='table')
            mock_echo.assert_called_once_with('test')
            mock_tabulate.assert_called_with([['bar']], headers=['foo'])

            command.format_response(data=[{'foo': 'bar'}, {'foo': 'bar2'}],
                                    format_type='table')
            mock_tabulate.assert_called_with(
                [['bar'], ['bar2']], headers=['foo'])

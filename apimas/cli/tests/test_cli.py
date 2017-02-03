import unittest
import mock
from apimas.cli import BaseCommand


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

import datetime
import unittest
import mock
from click.exceptions import BadParameter
from apimas.testing.helpers import create_mock_object
from apimas.cli.custom_types import (
    Email, Json, Date, DateTime, Credentials)


class TestCustomTypes(unittest.TestCase):

    def test_email(self):
        value = 'test@example.com'
        email = Email()
        output = email.convert(value, '', '')
        self.assertEqual(output, value)

        value = 'invalid email'
        self.assertRaises(BadParameter, email.convert, value, '', '')

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
        date_formats = ['%Y-%m-%d %H:%M', '%Y %M']
        datetime_obj = DateTime(date_formats)
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
        date_format = ['%Y-%m-%d', '%Y']
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
    @mock.patch('apimas.cli.custom_types.Credentials.load_yaml')
    @mock.patch('apimas.cli.custom_types.Credentials.load_json')
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

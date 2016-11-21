import unittest
import mock
from requests.exceptions import HTTPError
from apimas.modeling.clients import (
    ApimasClient, requests)
from apimas.modeling.clients.auth import HTTPTokenAuth, ApimasClientAuth
from apimas.modeling.core.exceptions import ApimasClientException


class TestClients(unittest.TestCase):
    def setUp(self):
        self.client = ApimasClient('http://endpoint/', {})

    def test_actions(self):
        actions = {
            'post': [(self.client.create, ())],
            'put': [(self.client.update, 1)],
            'patch': [(self.client.partial_update, 1)],
            'get': [(self.client.retrieve, 1), (self.client.list, ())],
            'delete': [(self.client.delete, 1)],
            'head': [(self.client.head, ())],
            'options': [(self.client.options, ())]
        }
        mock_response_ex = mock.MagicMock()
        mock_response_ex.raise_for_status.side_effect = HTTPError()
        mock_response = mock.MagicMock()
        for action, methods in actions.iteritems():
            with mock.patch.object(requests, action) as mock_action:
                for m, args in methods:
                    mock_action.return_value = mock_response_ex
                    self.assertRaises(ApimasClientException, m, args)
                    mock_action.return_value = mock_response
                    m(args)

    def test_partial_validate(self):
        validation_schema = {
            'field1': {
                'type': 'string',

            },
            'field2': {
                'type': 'string',
                'required': True
            }
        }
        self.client = ApimasClient('http://endpoint/', {})
        self.client.validation_schema = validation_schema
        data = {'field1': 1}
        self.assertRaises(ApimasClientException, self.client.partial_validate,
                          data)
        try:
            self.client.partial_validate(raise_exception=False, data=data)
            self.client.partial_validate(
                raise_exception=True, data={'field1': 'foo'})
        except ApimasClientException:
            self.fail()

    def test_extract_files(self):
        mock_file = mock.MagicMock(spec=file)
        data = {'field1': {'field2': mock_file}}
        self.assertRaises(ApimasClientException, self.client.extract_files,
                          data)
        data['field1']['field2'] = 'a value'
        data['field3'] = mock_file
        self.assertRaises(ApimasClientException, self.client.extract_files,
                          data)

        data = {'field1': 'a value', 'field2': mock_file,
                'field3': 'another value'}
        files = self.client.extract_files(data)
        self.assertEqual(files, {'field2': mock_file})
        self.assertEqual(data, {'field1': 'a value',
                                'field3': 'another value'})

    def test_extract_file_data(self):
        mock_client = mock.Mock(
            extract_write_data=ApimasClient.__dict__['extract_write_data'])
        mock_client.extract_write_data(mock_client, {}, True)
        self.assertEqual(mock_client.validate.call_count, 1)
        self.assertEqual(mock_client.partial_validate.call_count, 0)

        mock_client.extract_write_data(mock_client, {}, True,
                                       partial=True)

        self.assertEqual(mock_client.validate.call_count, 1)
        self.assertEqual(mock_client.partial_validate.call_count, 1)

        mock_client.extract_files.return_value = {}
        data = mock_client.extract_write_data(mock_client, {}, True)
        self.assertEqual(len(data), 1)
        self.assertIsNotNone(data['json'])

        mock_client.extract_files.return_value = 'a value'
        data = mock_client.extract_write_data(mock_client, {}, True)
        self.assertEqual(len(data), 2)
        self.assertIsNotNone(data['files'])
        self.assertIsNotNone(data['data'])


class TestAuth(unittest.TestCase):
    def test_token_auth(self):
        mock_token = 'my token'
        token_auth = HTTPTokenAuth(mock_token)
        mock_request = mock.Mock()
        mock_request.headers = {}
        token_auth(mock_request)
        self.assertEqual(mock_request.headers,
                         {'Authorization': 'Token ' + mock_token})

    def test_apimas_auth(self):
        mock_auth = mock.Mock()
        auth = ApimasClientAuth(None, **{})
        auth.AUTHENTICATION_BACKENDS = {'mock': mock_auth}
        mock_request = mock.Mock()
        mock_request.headers = {}
        auth(mock_request)

        self.assertEqual(mock_auth.call_count, 0)

        auth.auth_type = 'mock'
        auth(mock_request)
        self.assertEqual(mock_auth.call_count, 1)

        auth.auth_type = 'invalid'
        self.assertRaises(ApimasClientException, auth, mock_request)

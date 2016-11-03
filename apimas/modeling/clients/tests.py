import unittest
import mock
from requests.exceptions import HTTPError
from apimas.modeling.clients import (
    ApimasClient, requests)
from apimas.modeling.clients.auth import HTTPTokenAuth, ApimasClientAuth
from apimas.modeling.core.exceptions import ApimasClientException


class TestClients(unittest.TestCase):
    def test_actions(self):
        client = ApimasClient('http://endpoint/', {})
        actions = {
            'post': [(client.create, ())],
            'put': [(client.update, 1)],
            'patch': [(client.partial_update, 1)],
            'get': [(client.retrieve, 1), (client.list, ())],
            'delete': [(client.delete, 1)],
            'head': [(client.head, ())],
            'options': [(client.options, ())]
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
        client = ApimasClient('http://endpoint/', {})
        client.validation_schema = validation_schema
        data = {'field1': 1}
        self.assertRaises(ApimasClientException, client.partial_validate, data)
        try:
            client.partial_validate(raise_exception=False, data=data)
            client.partial_validate(
                raise_exception=True, data={'field1': 'foo'})
        except ApimasClientException:
            self.fail()


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

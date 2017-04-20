import unittest
import mock
from apimas.errors import ValidationError
from apimas.clients.auth import HTTPTokenAuth, ApimasClientAuth


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
        self.assertRaises(ValidationError, auth, mock_request)

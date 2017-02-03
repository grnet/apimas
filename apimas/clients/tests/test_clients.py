# -*- coding: utf-8 -*-

import unittest
import mock
from requests.exceptions import HTTPError
from apimas.clients import (
    ApimasClient, requests, get_subdocuments, to_cerberus_paths)
from apimas.exceptions import ApimasClientException
from apimas.testing.helpers import create_mock_object


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
            },
            'field3': {
                'type': 'dict',
                'schema': {
                    'field4': {
                        'type': 'string',
                        'required': True,
                    }
                }
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

        data['field3'] = {'field4': 10}
        self.assertRaises(ApimasClientException, self.client.partial_validate,
                          raise_exception=True, data=data)

    def test_partial_validate_sub(self):
        mock_client = create_mock_object(
            ApimasClient, ['_validate_subdata'])
        nested_schema = {
            'type': 'dict',
            'schema': {
                'field2': {
                    'type': 'string',
                    'required': True,
                },
                'field3': {
                    'type': 'string',
                    'required': True,
                }
            }
        }
        validation_schema = {
            'field': {
                'type': 'list',
                'schema': nested_schema
            },
            'field2': {
                'type': 'list',
                'schema': nested_schema,
            }
        }
        sub = {'field1': 'foo'}
        data = {'unknown': [sub]}
        self.assertRaises(ApimasClientException, mock_client._validate_subdata,
                          mock_client, data, validation_schema, False)
        mock_client.partial_validate.assert_not_called

        data = {'field': [sub], 'field2': [sub]}
        mock_client.partial_validate.return_value = sub
        validated = mock_client._validate_subdata(
            mock_client, data, validation_schema, raise_exception=False)
        self.assertEquals(validated, {('field',): [sub], ('field2',): [sub]})
        mock_client.partial_validate.assert_called

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

    def test_get_subdocuments(self):
        doc = {'foo': 'bar'}
        self.assertEquals(get_subdocuments(doc), {})
        doc_b = {'a': {'b': {'c': [doc, doc]}, 'd': [doc], 'c': [1, 2]}}
        output = {
            'a/b/c': [doc, doc],
            'a/d': [doc],
        }
        self.assertEquals(get_subdocuments(doc_b), output)

    def test_to_cerberus_paths(self):
        doc = {'a': {'b': {'c': {'foo': 1, 'bar': 2}}, 'd': 1}, 'b': []}
        output = [
            'a/schema/b/schema/c/schema/foo',
            'a/schema/b/schema/c/schema/bar',
            'a/schema/d'
        ]
        self.assertEquals(to_cerberus_paths(doc), output)

        doc = {}
        self.assertEquals(to_cerberus_paths(doc), [])

    def test_unicode(self):
        endpoint = self.client.format_endpoint(u"ύνικοδε")
        self.assertIsInstance(endpoint, str)

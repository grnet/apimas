# -*- coding: utf-8 -*-

import unittest
import mock
from requests.exceptions import HTTPError
from apimas.modeling.clients import (
    ApimasClient, ApimasClientAdapter, requests, get_subdocuments,
    to_cerberus_paths, TRAILING_SLASH, ApimasValidator)
from apimas.modeling.core.exceptions import (
    ApimasException, ApimasClientException)
from apimas.modeling.tests.helpers import create_mock_object
from apimas.modeling.adapters.cookbooks import NaiveAdapter


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


class TestClientAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter_conf = ApimasClientAdapter.ADAPTER_CONF

    def test_get_client(self):
        mock_client = create_mock_object(ApimasClientAdapter, ['get_client'])
        mock_client.clients = {}
        self.assertRaises(ApimasException, mock_client.get_client,
                          mock_client, endpoint='api', collection='collection')
        mock_clients = {'api/collection': 'value'}
        mock_client.clients = mock_clients
        value = mock_client.get_client(mock_client, endpoint='api',
                                       collection='collection')
        self.assertEquals(value, mock_clients['api/collection'])

    @mock.patch(
        'apimas.modeling.adapters.cookbooks.NaiveAdapter.construct_collection')
    @mock.patch('apimas.modeling.clients.clients.ApimasValidator')
    def test_construct_collection(self, mock_validator, mock_constructor):
        mock_client = create_mock_object(
            ApimasClientAdapter, ['construct_collection', 'ADAPTER_CONF'],
            ismagic=True)
        mock_client.clients = {}
        mock_client.__class__.__bases__ = (NaiveAdapter,)
        mock_client.root_url = 'http://example.com'
        mock_instance = {
            '*': {
                'field1': {
                    self.adapter_conf: {'foo': 'bar'},
                    'another': {},
                },
                'field2': {
                    self.adapter_conf: {'bar': 'foo'},
                }
            }
        }
        context = {'parent_name': 'foo'}
        loc = ('api', 'collection', '.collection')
        mock_constructor.return_value = mock_instance
        instance = mock_client.construct_collection(
            mock_client, mock_instance, {}, loc, context=context)
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf['field1'], {'foo': 'bar'})
        self.assertEqual(instance_conf['field2'], {'bar': 'foo'})
        mock_constructor.assert_called_once

        # Assert client construction.
        self.assertEqual(len(mock_client.clients), 1)
        client = mock_client.clients.get('api/foo')
        self.assertTrue(isinstance(client, ApimasClient))
        self.assertEqual(client.endpoint, 'http://example.com/api/foo/')

        self.assertTrue(isinstance(client.api_validator, mock.Mock))
        mock_validator.assert_called_once_with({'field1': {'foo': 'bar'},
                                                'field2': {'bar': 'foo'}})

    def test_construct_field(self):
        mock_instance = {'foo': {'bar': {}}, self.adapter_conf: {}}
        mock_loc = ('foo', 'bar')
        mock_client = create_mock_object(ApimasClientAdapter,
                                         ['construct_field', 'ADAPTER_CONF'])
        mock_client.init_adapter_conf.return_value = mock_instance
        mock_client.extract_type.return_value = None
        mock_client.get_extra_params.return_value = {'extra': 'value'}

        # Case A: Unspecified type.
        self.assertRaises(ApimasException, mock_client.construct_field,
                          mock_client, mock_instance, {}, mock_loc, {})
        mock_client.extract_type.assert_called_once_with(mock_instance)

        # Case B: Structural elements.
        nested_structures = {'.struct', '.structarray'}
        expected = {'foo'}
        mock_client.construct_nested_field.return_value = expected
        for structure in nested_structures:
            mock_client.extract_type.return_value = structure
            instance = mock_client.construct_field(
                mock_client, mock_instance, {}, mock_loc, {})
            self.assertEqual(instance, expected)
            mock_client.construct_nested_field.assert_called
            mock_client.init_adapter_conf.assert_called_with(mock_instance)
            mock_client.extract_type.assert_called_with(mock_instance)

        # Case C:  A common field.
        mock_client.extract_type.return_value = 'foo'
        instance = mock_client.construct_field(
            mock_client, mock_instance, {}, mock_loc, {})
        self.assertEqual(instance[self.adapter_conf]['extra'], 'value')
        mock_client.init_adapter_conf.assert_called_with(mock_instance)
        mock_client.extract_type.assert_called_with(mock_instance)
        mock_client.get_extra_params.assert_called_once

        # Case D: A date/datetime field.
        fields = {'.date', '.datetime'}
        for field_type in fields:
            mock_client.extract_type.return_value = field_type
            mock_client._construct_date_field.return_value = (
                field_type + '_returned')
            instance = mock_client.construct_field(
                mock_client, mock_instance, {}, mock_loc, {})
            self.assertEqual(instance, field_type + '_returned')

    @mock.patch('apimas.modeling.clients.clients.RefNormalizer')
    @mock.patch(
        'apimas.modeling.adapters.cookbooks.NaiveAdapter.construct_ref')
    def test_construct_ref(self, mock_constructor, mock_normalizer):
        mock_root_url = 'mock'
        mock_client = create_mock_object(ApimasClientAdapter,
                                         ['construct_ref', 'ADAPTER_CONF'])
        mock_client.__class__.__bases__ = (NaiveAdapter,)
        mock_client.root_url = mock_root_url
        mock_loc = ('foo', 'bar')
        mock_instance = {self.adapter_conf: {}}
        mock_constructor.return_value = mock_instance
        spec = {'to': 'foo'}
        instance = mock_client.construct_ref(
            mock_client, mock_instance, spec, mock_loc, {})
        self.assertEqual(len(instance), 1)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertTrue(isinstance(instance_conf['coerce'], mock.MagicMock))
        mock_normalizer.assert_called_once_with(
            TRAILING_SLASH.join((mock_root_url, mock_loc[0], 'foo', '')))

        spec['many'] = True
        instance = mock_client.construct_ref(
            mock_client, mock_instance, spec, mock_loc, {})
        self.assertEqual(len(instance), 1)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 2)
        self.assertEqual(instance_conf['type'], 'list')
        self.assertTrue(isinstance(instance_conf['schema']['coerce'],
                        mock.MagicMock))
        mock_normalizer.assert_called_with(
            TRAILING_SLASH.join((mock_root_url, mock_loc[0], 'foo', '')))

    def test_construct_nested_field(self):
        mock_loc = ('foo', 'bar')
        mock_client = create_mock_object(
            ApimasClientAdapter, ['construct_nested_field', 'ADAPTER_CONF'])
        schema = {
            'field1': {
                self.adapter_conf: {'foo': 'bar'},
                'another': {},
            },
            'field2': {
                self.adapter_conf: {'bar': 'foo'},
            }
        }
        mock_instance = {'.struct': schema, self.adapter_conf: {}}
        instance = mock_client.construct_nested_field(
            mock_client, mock_instance, {}, mock_loc, {}, '.struct')
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf['type'], 'dict')
        self.assertEqual(instance_conf['schema'], {'field1': {'foo': 'bar'},
                                                   'field2': {'bar': 'foo'}})

        mock_instance = {'.structarray': schema, self.adapter_conf: {}}
        instance = mock_client.construct_nested_field(
            mock_client, mock_instance, {}, mock_loc, {}, '.structarray')
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf['type'], 'list')

        schema = instance_conf['schema']
        self.assertEqual(schema['type'], 'dict')
        self.assertEqual(schema['schema'], {'field1': {'foo': 'bar'},
                                            'field2': {'bar': 'foo'}})

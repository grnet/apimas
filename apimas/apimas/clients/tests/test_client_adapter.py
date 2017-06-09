import unittest
import mock
from apimas.errors import InvalidSpec, NotFound
from apimas.adapters.cookbooks import NaiveAdapter
from apimas.clients import TRAILING_SLASH, ApimasClient
from apimas.clients.adapter import ApimasClientAdapter
from apimas.testing.helpers import (
    create_mock_object, create_mock_constructor_context)


class TestClientAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter_conf = ApimasClientAdapter.ADAPTER_CONF

    def test_get_client(self):
        mock_client = create_mock_object(ApimasClientAdapter, ['get_client'])
        mock_client.clients = {}
        self.assertRaises(NotFound, mock_client.get_client,
                          mock_client, endpoint='api', collection='collection')
        mock_clients = {'api/collection': 'value'}
        mock_client.clients = mock_clients
        value = mock_client.get_client(mock_client, endpoint='api',
                                       collection='collection')
        self.assertEquals(value, mock_clients['api/collection'])

    @mock.patch(
        'apimas.adapters.cookbooks.NaiveAdapter.construct_collection')
    @mock.patch('apimas.clients.clients.CerberusValidator')
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
        loc = ('api', 'collection', '.collection')
        mock_context = create_mock_constructor_context(
            instance=mock_instance, loc=loc, parent_name='foo')
        mock_constructor.return_value = mock_instance
        instance = mock_client.construct_collection(
            mock_client, context=mock_context)
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
        mock_context = create_mock_constructor_context(
            instance=mock_instance, loc=mock_loc)

        # Case A: Unspecified type.
        self.assertRaises(InvalidSpec, mock_client.construct_field,
                          mock_client, context=mock_context)
        mock_client.extract_type.assert_called_once_with(mock_instance)

        # Case B: Structural elements.
        nested_structures = {'.struct', '.structarray'}
        expected = {'foo'}
        mock_client.construct_nested_field.return_value = expected
        for structure in nested_structures:
            mock_client.extract_type.return_value = structure
            instance = mock_client.construct_field(
                mock_client, context=mock_context)
            self.assertEqual(instance, expected)
            mock_client.construct_nested_field.assert_called
            mock_client.init_adapter_conf.assert_called_with(mock_instance)
            mock_client.extract_type.assert_called_with(mock_instance)

        # Case C:  A common field.
        mock_client.extract_type.return_value = 'foo'
        instance = mock_client.construct_field(
            mock_client, context=mock_context)
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
                mock_client, context=mock_context)
            self.assertEqual(instance, field_type + '_returned')

    @mock.patch('apimas.clients.adapter.RefNormalizer')
    @mock.patch(
        'apimas.adapters.cookbooks.NaiveAdapter.construct_ref')
    def test_construct_ref(self, mock_constructor, mock_normalizer):
        mock_root_url = 'mock'
        mock_client = create_mock_object(ApimasClientAdapter,
                                         ['construct_ref', 'ADAPTER_CONF'])
        mock_client.__class__.__bases__ = (NaiveAdapter,)
        mock_client.root_url = mock_root_url
        mock_loc = ('foo', 'bar')
        mock_instance = {self.adapter_conf: {}}
        mock_constructor.return_value = mock_instance
        mock_spec = {'to': 'foo'}
        mock_context = create_mock_constructor_context(
            instanccee=mock_instance, spec=mock_spec, loc=mock_loc)
        instance = mock_client.construct_ref(
            mock_client, context=mock_context)
        self.assertEqual(len(instance), 1)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertTrue(isinstance(instance_conf['coerce'], mock.MagicMock))
        mock_normalizer.assert_called_once_with(
            TRAILING_SLASH.join((mock_root_url, mock_loc[0], 'foo', '')))

        mock_spec['many'] = True
        mock_context = create_mock_constructor_context(
            instanccee=mock_instance, spec=mock_spec, loc=mock_loc)
        instance = mock_client.construct_ref(mock_client, context=mock_context)
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
        mock_instance = {'.struct=': schema, self.adapter_conf: {}}
        mock_context = create_mock_constructor_context(
            instance=mock_instance, loc=mock_loc)
        instance = mock_client.construct_nested_field(
            mock_client, mock_context, '.struct')
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf['type'], 'dict')
        self.assertEqual(instance_conf['schema'], {'field1': {'foo': 'bar'},
                                                   'field2': {'bar': 'foo'}})

        mock_instance = {'.structarray=': schema, self.adapter_conf: {}}
        mock_context = create_mock_constructor_context(
            instance=mock_instance, loc=mock_loc)
        instance = mock_client.construct_nested_field(
            mock_client, mock_context, '.structarray')
        self.assertEqual(len(instance), 2)
        instance_conf = instance.get(mock_client.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf['type'], 'list')

        schema = instance_conf['schema']
        self.assertEqual(schema['type'], 'dict')
        self.assertEqual(schema['schema'], {'field1': {'foo': 'bar'},
                                            'field2': {'bar': 'foo'}})

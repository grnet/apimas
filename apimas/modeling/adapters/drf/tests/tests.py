import mock
import unittest
from apimas.modeling.tests import helpers
from apimas.modeling.core import documents as doc
from apimas.modeling.adapters.drf import utils
from apimas.modeling.adapters.drf.django_rest import DjangoRestAdapter
from apimas.modeling.adapters.drf import serializers
from apimas.modeling.adapters.drf.serializers import (
    get_paths, validate, generate)


def create_mock_DRF(method_name):
    non_mock_attrs = [
        method_name,
        'ADAPTER_CONF',
        'NESTED_CONF_KEY',
        'PROPERTIES_CONF_KEY'
    ]
    return helpers.create_mock_object(DjangoRestAdapter, non_mock_attrs)


class TestSerializers(unittest.TestCase):
    def setUp(self):
        self.mock_field = mock.MagicMock()
        self.mock_meta = mock.MagicMock()
        self.mock_meta.get_field.return_value = self.mock_field
        self.mock_model = mock.MagicMock(_meta=self.mock_meta)

    def test_get_paths(self):
        fields = {'field1': 'value', 'field2': 'value'}
        mock_sera = mock.MagicMock(fields=fields)
        paths = get_paths(mock_sera.fields)
        self.assertEqual(len(paths), 2)
        for p in ['field1', 'field2']:
            self.assertIn(p, paths)

        nested_fields = {'field': mock_sera}
        mock_serb = mock.MagicMock(fields=nested_fields)
        paths = get_paths(mock_serb.fields)
        self.assertEqual(len(paths), 3)
        for p in ['field', 'field/field1', 'field/field2']:
            self.assertIn(p, paths)

        # Test a 3-level serializer
        nested_fields = {'field1': 'a value', 'nested': mock_serb}
        mock_serc = mock.MagicMock(child=nested_fields)
        paths = get_paths(mock_serc.child)
        self.assertEqual(len(paths), 5)
        for p in ['field1', 'nested/field',
                  'nested/field/field1', 'nested/field/field2']:
            self.assertIn(p, paths)

    def test_validate(self):
        non_intersectional_pairs = [('prop_a', 'prop_c')]
        serializers.NON_INTERSECTIONAL_PAIRS = non_intersectional_pairs
        field_properties = {
            'field1': {
                'prop_a': True,
                'prop_c': True,
            }
        }
        self.assertRaises(utils.DRFAdapterException, validate, self.mock_model,
                          field_properties)

        field_properties['field1']['prop_a'] = False
        validate(self.mock_model, field_properties)

        self.mock_field.get_internal_type.return_value = 'non_string'
        field_properties['field1']['allow_blank'] = True
        self.assertRaises(utils.DRFAdapterException, validate, self.mock_model,
                          field_properties)

    def test_generate(self):
        config = {
            'fields': ['field1', 'field2'],
            'read_only_fields': ['field1'],
            'required_fields': ['field2'],
            'nullable_fields': ['field2'],
            'write_only_fields': ['field2'],
        }
        self.mock_model.__name__ = 'Mock'
        serializer_cls = generate(self.mock_model, config)
        meta = serializer_cls.Meta
        self.assertIsNotNone(meta)
        self.assertEqual(meta.fields, ['field1', 'field2'])
        extra_kwargs = {
            'field1': {
                'read_only': True,
            },
            'field2': {
                'required': True,
                'allow_null': True,
                'write_only': True,
            }
        }
        self.assertEqual(meta.extra_kwargs, extra_kwargs)


class TestDjangoRestAdapter(unittest.TestCase):
    loc = ('a', 'b', 'c')
    context = {'top_spec': {}}
    mock_type_mapping = {'type': 'value'}

    def setUp(self):
        self.adapter = DjangoRestAdapter()
        self.adapter_conf = self.adapter.ADAPTER_CONF

    def test_construct_CRUD_action(self):
        instance = {}
        action = 'myaction'
        instance = self.adapter.construct_CRUD_action(
                instance, None, None, None, action)
        allowable_actions = {'allowable_operations': [action]}
        self.assertEqual(instance, {
            self.adapter_conf: allowable_actions})
        instance = self.adapter.construct_CRUD_action(
                instance, None, None, None, action)
        instance_actions = instance[self.adapter_conf][
            'allowable_operations']
        self.assertEqual(instance_actions, [action, action])

    def test_construct_endpoint(self):
        spec = {
            'api': {
                'resource1': {
                    self.adapter_conf: {
                        'k1': 'v1'
                    }
                },
                'resource2': {
                    self.adapter_conf: {
                        'k2': 'v2'
                    }
                }
            }
        }
        instance = self.adapter.construct_endpoint(spec, spec, None, None)
        instance_conf = instance.get(self.adapter_conf)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 1)
        for k, v in instance_conf['resources'].iteritems():
            self.assertIn(k, spec['api'])
            self.assertEqual(v, spec['api'][k][self.adapter_conf])

    def test_construct_collection(self):
        spec = {'a': 'value', 'b': 'value'}
        instance = {}
        self.assertRaises(doc.DeferConstructor,
                          self.adapter.construct_collection, instance, spec,
                          None, None)
        instance = {self.adapter_conf: {}}
        instance = self.adapter.construct_collection(instance, spec, None,
                                                     None)
        self.assertEqual(len(instance), 1)
        instance_conf = instance.get(self.adapter_conf)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf, spec)

    def test_construct_drf_collection(self):
        self.assertRaises(utils.DRFAdapterException,
                          self.adapter.construct_drf_collection,
                          {}, {}, self.loc, None)
        instance = {
            '*': {
                'field1': {},
            },
            self.adapter_conf: {}
        }
        mock_adapter = create_mock_DRF('construct_drf_collection')
        field_schema = {'field_schema': {}}
        resource_schema = {'resource_schema': {}}
        mock_adapter.construct_field_schema.return_value = field_schema
        mock_adapter.construct_resource_schema.return_value = resource_schema
        instance = mock_adapter.construct_drf_collection(
            mock_adapter, instance, {}, self.loc, None)
        instance_conf = instance.get(self.adapter_conf)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf, dict(field_schema, **resource_schema))
        mock_adapter.construct_field_schema.assert_called_once
        mock_adapter.construct_resource_schema.assert_called_once

    def test_construct_nested_drf_field(self):
        mock_adapter = create_mock_DRF('construct_nested_drf_field')
        mock_adapter.TYPE_MAPPING = self.mock_type_mapping
        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.construct_nested_drf_field,
                          mock_adapter, {}, {}, self.loc, None, '.type')
        instance = {
            self.adapter_conf: {mock_adapter.PROPERTIES_CONF_KEY: {}},
            '.type': {
                'field': {}
            }
        }
        field_schema = {'field_schema': {}}
        source = 'source'
        spec = {'a': 'value', 'source': source}
        mock_adapter.construct_field_schema.return_value = field_schema
        instance = mock_adapter.construct_nested_drf_field(
            mock_adapter, instance, spec, self.loc, self.context, '.type')
        instance_conf = instance.get(self.adapter_conf)
        self.assertIsNotNone(instance_conf)
        properties = instance_conf.get(mock_adapter.PROPERTIES_CONF_KEY)
        self.assertIsNotNone(properties)
        self.assertEqual(properties, spec)
        mock_adapter.validate_model_field.assert_called_once_with(
            {}, self.loc, 'value', source)

        nested = instance_conf.get(mock_adapter.NESTED_CONF_KEY)
        self.assertIsNotNone(nested)
        self.assertEqual(nested, dict(field_schema, **{'source': source}))
        self.assertEqual(mock_adapter.construct_field_schema.call_count, 1)

    def test_default_field_constructor(self):
        spec = {'key': 'value'}
        mock_adapter = create_mock_DRF(
            'default_field_constructor')
        mock_type_mapping = dict(self.mock_type_mapping, **{'ref': 'value'})
        mock_adapter.TYPE_MAPPING = mock_type_mapping
        instance = {
            self.adapter_conf: {mock_adapter.PROPERTIES_CONF_KEY: {}},
        }
        instance = mock_adapter.default_field_constructor(
            mock_adapter, instance, spec, self.loc, self.context, '.type')
        instance_conf = instance.get(mock_adapter.ADAPTER_CONF)
        mock_adapter.validate_model_field.assert_called_once_with(
            {}, self.loc, 'value', None)
        mock_adapter.validate_ref.assert_not_called
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 1)
        properties = instance_conf.get(mock_adapter.PROPERTIES_CONF_KEY)
        self.assertIsNotNone(properties)
        self.assertEqual(properties, spec)

        instance = mock_adapter.default_field_constructor(
            mock_adapter, instance, spec, self.loc, self.context, '.ref')
        mock_adapter.validate_ref.assert_called_once

    def test_construct_drf_field(self):
        context = {'top_spec': {}}
        mock_adapter = create_mock_DRF('construct_drf_field')
        mock_adapter.TYPE_MAPPING = self.mock_type_mapping
        self.assertRaises(doc.DeferConstructor,
                          mock_adapter.construct_drf_field,
                          mock_adapter, {}, {}, self.loc, context)
        instance = {self.adapter_conf: {}}
        mock_adapter.extract_type.return_value = 'value'
        output = mock_adapter.construct_drf_field(
            mock_adapter, instance, {}, self.loc, context)
        instance_conf = output.get(mock_adapter.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        properties = instance_conf.get(mock_adapter.PROPERTIES_CONF_KEY)
        self.assertIsNotNone(properties)
        mock_adapter.default_field_constructor.assert_called_once
        mock_adapter.construct_nested_drf_field.assert_not_called
        mock_adapter.extract_type.assert_called_once_with

        structures = {'.struct', '.structarray'}
        for i, structure in enumerate(structures, 1):
            mock_adapter.extract_type.return_value = structure
            mock_adapter.construct_drf_field(
                mock_adapter, instance, {}, self.loc, context)
            self.assertEqual(
                mock_adapter.default_field_constructor.call_count, 1)
            self.assertEqual(
                mock_adapter.construct_nested_drf_field.call_count, i)
            self.assertEqual(mock_adapter.extract_type.call_count, i + 1)

    def test_construct_property(self):
        self.assertRaises(doc.DeferConstructor,
                          self.adapter.construct_property,
                          {}, {}, None, None, None)
        instance = {self.adapter_conf: {}}
        property_name = 'property'
        self.adapter.PROPERTY_MAPPING = {property_name: property_name}
        instance = self.adapter.construct_property(instance, {}, None, None,
                                                   property_name)
        instance_conf = instance.get(self.adapter_conf)
        self.assertIsNotNone(instance_conf)
        properties = instance_conf.get(self.adapter.PROPERTIES_CONF_KEY)
        self.assertIsNotNone(properties)
        self.assertEqual(len(properties), 1)
        self.assertTrue(properties[property_name])

    def test_validate_model_field(self):
        mock_adapter = create_mock_DRF('validate_model_field')
        mock_adapter.TYPE_MAPPING = self.mock_type_mapping
        mock_cls = type('mock', (object,), {})
        mock_cls2 = type('mock2', (object,), {})
        field_type = mock_cls
        mock_adapter.extract_model.return_value = None
        mock_meta = mock.Mock()
        mock_meta.get_field.return_value = mock_cls()
        mock_model = mock.Mock(_meta=mock_meta)

        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.validate_model_field, mock_adapter,
                          None, self.loc, field_type, None)
        mock_meta.get_field.assert_not_called

        source = 'myvalue'
        mock_adapter.extract_model.return_value = mock_model
        mock_adapter.validate_model_field(mock_adapter, None, self.loc,
                                          field_type, source)
        mock_meta.get_field.assert_called_once_with(source)

        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.validate_model_field,
                          mock_adapter, None, self.loc, mock_cls2, source)

    def tests_validate_intersectional_pairs(self):
        mock_pairs = [
            ('a', 'b')
        ]
        self.adapter.NON_INTERSECTIONAL_PAIRS = mock_pairs
        properties = {
            'field1': {
                'a': True,
                'b': True
            },
            'field2': {
                'c': True
            }
        }
        self.assertRaises(utils.DRFAdapterException,
                          self.adapter.validate_intersectional_pairs,
                          properties)
        properties['field1']['a'] = False
        self.adapter.validate_intersectional_pairs(properties)

    def test_construct_field_schema(self):
        mock_type_mapping = {'type': 'value', 'ref': 'value'}
        mock_adapter = create_mock_DRF('construct_field_schema')
        mock_adapter.TYPE_MAPPING = mock_type_mapping
        mock_properties = {
            'field1': {
                self.adapter_conf: {
                    mock_adapter.PROPERTIES_CONF_KEY: {
                        'key': 'value',
                    }
                }
            },
            'field2': {
                self.adapter_conf: {
                    mock_adapter.NESTED_CONF_KEY: {
                        'key2': 'value2',
                    }
                }
            }
        }
        instance = {self.adapter_conf: {}}
        serializers = ['myserializer']
        instance = mock_adapter.construct_field_schema(
            mock_adapter, instance, mock_properties, serializers=serializers)
        self.assertEqual(len(instance), 1)
        field_schema = instance.get('field_schema')
        self.assertIsNotNone(field_schema)
        self.assertEqual(len(field_schema), 4)
        self.assertEqual(field_schema['fields'], mock_properties.keys())
        self.assertEqual(field_schema['serializers'], serializers)
        self.assertEqual(
            field_schema[mock_adapter.PROPERTIES_CONF_KEY],
            {'field1': {'key': 'value'}})
        self.assertEqual(
            field_schema[mock_adapter.NESTED_CONF_KEY],
            {'field2': {'key2': 'value2'}})

    def test_get_constructor_params(self):
        mock_structures = {
            'a': 'b',
            'b': 'a',
        }
        self.adapter.STRUCTURES = mock_structures
        mock_spec = {
            'a': {'a1': 'va1'},
            'key': {
                'b': {'b1': 'vb1'},
                'a': {'a2': 'va2'},
                'key': {
                    'key': {
                        'b': {'b2': 'vb2'},
                        'one_more': {},
                    }
                }
            }
        }
        loc = ('key', 'key', 'key', 'one_more')
        output = self.adapter.get_constructor_params(mock_spec, loc, [])
        self.assertEqual(len(output), 2)
        self.assertEqual(output[0], ('a', {'b1': 'vb1'}))
        self.assertEqual(output[1], ('b', {'a2': 'va2'}))

    def test_extract_related_model(self):
        output = mock.Mock(related_model=None)
        mock_meta = mock.Mock()
        mock_meta.get_field.return_value = output
        mock_model = mock.Mock(_meta=mock_meta)
        mock_adapter = create_mock_DRF('extract_related_model')
        mock_adapter.extract_model.return_value = mock_model
        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.extract_related_model,
                          mock_adapter, None, None)

        output = mock.Mock(related_model='value')
        mock_meta.get_field.return_value = output
        output = mock_adapter.extract_related_model(
            mock_adapter, None, None)
        self.assertEqual(output, 'value')

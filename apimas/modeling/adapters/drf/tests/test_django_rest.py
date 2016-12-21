import mock
import unittest
from apimas.modeling.core import documents as doc
from apimas.modeling.adapters.drf import utils
from apimas.modeling.adapters.drf.django_rest import DjangoRestAdapter
from apimas.modeling.tests.helpers import create_mock_object


class TestDjangoRestAdapter(unittest.TestCase):
    loc = ('a', 'b', 'c')
    context = {'top_spec': {}}
    mock_type_mapping = {'type': 'value'}

    def setUp(self):
        self.adapter = DjangoRestAdapter()
        self.adapter_conf = self.adapter.ADAPTER_CONF

    def test_get_class(self):
        empty = {}
        self.assertRaises(utils.DRFAdapterException, self.adapter.get_class,
                          empty, 'something')
        container = {'foo': 'bar'}
        self.assertRaises(utils.DRFAdapterException, self.adapter.get_class,
                          container, 'something')
        self.assertEqual(self.adapter.get_class(container, 'foo'), 'bar')

    #def test_get_permissions(self):
    #    rules = [
    #        ('foo', 'a', 'b', 'c', 'd', 'e'),
    #        ('foo', 'a', 'b', 'c', 'f', 'k'),
    #        ('*', 'a', 'b', 'c', 'p', 'l'),
    #        ('bar', 'z', 'l', 'm', '*', '*')
    #    ]
    #    top_spec = {}
    #    self.assertIsNone(self.adapter.get_permissions('foo', top_spec))

    #    top_spec = {'.endpoint': {'permissions': rules}}
    #    permissions = self.adapter.get_permissions('foo', top_spec)
    #    self.assertEqual(len(permissions), 3)

    def test_construct_CRUD_action(self):
        instance = {}
        action = 'myaction'
        instance = self.adapter.construct_CRUD_action(
            instance, None, None, None, action)
        allowable_actions = [action]
        self.assertEqual(instance, {
            self.adapter_conf: allowable_actions})
        instance = self.adapter.construct_CRUD_action(
            instance, None, None, None, action)
        instance_actions = instance[self.adapter_conf]
        self.assertEqual(instance_actions, [action, action])

    @mock.patch(
        'apimas.modeling.adapters.drf.django_rest.generate_container_serializer',
        return_value='mock_container')
    @mock.patch(
        'apimas.modeling.adapters.drf.django_rest.generate_model_serializer',
        return_value='mock_model')
    def test_generate_serializer(self, mock_model_ser, mock_container_ser):
        mock_adapter = create_mock_object(
            DjangoRestAdapter, ['generate_serializer'])
        model_fields = {'model_fields': 'value'}
        extra_fields = {'extra_fields': 'value'}
        instance_sources = {'instance_source': 'value'}
        mock_adapter._classify_fields.return_value = (
            model_fields, extra_fields, instance_sources)
        field_schema = {'foo', 'bar'}
        name = 'mock_serializer'
        serializer = mock_adapter.generate_serializer(
            mock_adapter, field_schema, name)
        self.assertEqual(serializer, 'mock_container')
        mock_container_ser.assert_called_once_with(
            model_fields, extra_fields, name, None,
            instance_sources=instance_sources,
            model_serializers=None,
            extra_serializers=None)
        mock_model_ser.assert_not_called

        mock_model = mock.Mock()
        serializer = mock_adapter.generate_serializer(
            mock_adapter, field_schema, name, model=mock_model,
            onmodel=True)
        self.assertEqual(serializer, 'mock_model')
        mock_model_ser.assert_called_once_with(
            name, mock_model, model_fields,
            bases=None)
        mock_container_ser.assert_called_once

    @mock.patch(
        'apimas.modeling.adapters.drf.django_rest.generate_view',
        return_value='mock_view')
    def test_contruct_drf_collection(self, mock_view_gen):
        mock_loc = ('api', 'collection', '.drf_collection')
        mock_instance = {
            '*': {
                'foo': {},
                'bar': {},
            },
            'actions': {
                self.adapter_conf: ['a', 'b']
            },
            self.adapter_conf: {},
        }
        mock_spec = {
            'serializers': ['ser_cls'],
            'model_serializers': ['model_ser_cls'],
            'model': 'model_cls',
        }
        mock_adapter = create_mock_object(
            DjangoRestAdapter, ['construct_drf_collection', 'ADAPTER_CONF'])
        mock_adapter._get_or_import_model.return_value = 'model_imported'
        mock_adapter.views = {}
        mock_adapter.serializers = {}
        mock_adapter.generate_serializer.return_value = 'mock_serializer'
        mock_adapter.get_permissions.return_value = 'permissions'
        context = {'constructed': ['.a_constructor'],
                   'parent_name': 'collection'}
        self.assertRaises(doc.DeferConstructor,
                          mock_adapter.construct_drf_collection, mock_adapter,
                          instance=mock_instance, spec=mock_spec, loc=mock_loc,
                          context=context)

        context['constructed'] = ['.collection']
        instance = mock_adapter.construct_drf_collection(
            mock_adapter, instance=mock_instance, spec=mock_spec,
            loc=mock_loc, context=context)
        self.assertEqual(len(instance), 3)
        self.assertIn('*', instance)
        self.assertIn('actions', instance)
        instance_conf = instance.get(self.adapter_conf)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(instance_conf, 'mock_view')
        self.assertEqual(mock_adapter.views['collection'], 'mock_view')
        self.assertEqual(mock_adapter.serializers['collection'],
                         'mock_serializer')
        mock_adapter._get_or_import_model.assert_called_once_with(
            'collection', mock_loc + ('model',), None)
        mock_view_gen.assert_called_once_with(
            'collection', 'mock_serializer', 'model_imported',
            actions=['a', 'b'], permissions='permissions')

    def test_classify_fields(self):
        field_schema = {
            'foo': {
                self.adapter_conf: {'field': 'foo_field'},
                '.drf_field': {},
            },
            'bar': {
                self.adapter_conf: {'field': 'bar_field'},
                '.drf_field': {'onmodel': False, 'instance_source': 'mock'}
            }
        }
        model_fields, extra_fields, instance_sources = self.adapter\
            ._classify_fields(field_schema)
        self.assertEqual(len(model_fields), 1)
        self.assertEqual(model_fields['foo'], 'foo_field')

        self.assertEqual(len(extra_fields), 1)
        self.assertEqual(extra_fields['bar'], 'bar_field')

    def test_get_default_paremeters(self):
        kwargs = {'required': True}
        predicate_type = '.string'
        default = self.adapter.get_default_properties(predicate_type,
                                                      kwargs)
        self.assertEqual(len(default), len(self.adapter.PROPERTY_MAPPING) - 1)
        for prop in self.adapter.PROPERTY_MAPPING.itervalues():
            self.assertFalse(default.get(prop))
        predicate_type = '.integer'
        default = self.adapter.get_default_properties(predicate_type,
                                                      kwargs)
        self.assertEqual(len(default), len(self.adapter.PROPERTY_MAPPING) - 2)
        for prop in self.adapter.PROPERTY_MAPPING.itervalues():
            if prop == 'allow_blank':
                self.assertIsNone(default.get(prop))
                continue
            self.assertFalse(default.get(prop))

    def test_generate_field(self):
        mock_a = mock.Mock(return_value='foo_field')
        mock_b = mock.Mock(return_value='bar_field')
        mock_serializer_mapping = {
            'foo': mock_a,
            'bar': mock_b,
        }
        mock_adapter = create_mock_object(
            DjangoRestAdapter,
            ['_generate_field', 'ADAPTER_CONF', 'STRUCTURES'])
        mock_adapter.SERILIZERS_TYPE_MAPPING = mock_serializer_mapping
        mock_adapter.generate_nested_drf_field.return_value = 'nested_field'
        self.assertIn('.struct', mock_adapter.STRUCTURES)
        self.assertIn('.structarray', mock_adapter.STRUCTURES)

        for predicate_type in ['.struct', '.structarray']:
            field = mock_adapter._generate_field(
                mock_adapter, instance={}, loc=(),
                predicate_type=predicate_type, model=None, onmodel=True)
            self.assertEqual(field, 'nested_field')
            mock_adapter.generate_nested_drf_field.assert_called_with(
                {}, (), predicate_type, None, onmodel=True)

        predicate_type = '.foo'
        mock_adapter.get_default_properties.return_value = {}
        self.assertNotIn(predicate_type, mock_adapter.STRUCTURES)
        field = mock_adapter._generate_field(
            mock_adapter, instance={}, loc=(),
            predicate_type=predicate_type, model=None, onmodel=False)
        self.assertEqual(field, 'foo_field')
        mock_a.assert_called_with()
        mock_b.assert_not_called

        field = mock_adapter._generate_field(
            mock_adapter, instance={}, loc=(),
            predicate_type=predicate_type, model=None, onmodel=True)
        self.assertEqual(field, {})

    def test_default_field_constructor(self):
        mock_instance = {
            '.string': {},
            self.adapter_conf: {},
        }
        mock_spec = {
            'onmodel': True,
            'extra': 'value',
            'foo': 'bar',
            'instance_source': 'instance_mock',
        }
        mock_loc = ('api', 'foo', '*', 'field', '.drf_field')
        mock_adapter = create_mock_object(
            DjangoRestAdapter, ['default_field_constructor', 'ADAPTER_CONF'])
        mock_adapter._generate_field.return_value = 'drf field'
        self.assertRaises(
            utils.DRFAdapterException, mock_adapter.default_field_constructor,
            mock_adapter, instance=mock_instance, spec=mock_spec,
            loc=mock_loc, context={}, predicate_type='.string')
        mock_spec['onmodel'] = False
        mock_spec['instance_source'] = 'instance_mock'

        instance = mock_adapter.default_field_constructor(
            mock_adapter, instance=mock_instance, spec=mock_spec,
            loc=mock_loc, context={}, predicate_type='.string')
        instance_conf = instance.get(mock_adapter.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 2)
        self.assertEqual(instance_conf['field'], 'drf field')
        self.assertEqual(instance_conf['source'], 'instance_mock')
        field_kwargs = {'extra': 'value', 'foo': 'bar'}
        mock_adapter._generate_field.assert_called_with(
            mock_instance, mock_loc, '.string', mock.ANY, False,
            **field_kwargs)

        mock_instance = {
            '.ref': {'to': 'bar'},
            self.adapter_conf: {},
        }
        mock_spec['instance_source'] = 'instance_mock'
        instance = mock_adapter.default_field_constructor(
            mock_adapter, instance=mock_instance, spec=mock_spec,
            loc=mock_loc, context={}, predicate_type='.ref')
        instance_conf = instance.get(mock_adapter.ADAPTER_CONF)
        self.assertIsNotNone(instance_conf)
        self.assertEqual(len(instance_conf), 2)
        self.assertEqual(instance_conf['field'], 'drf field')
        self.assertEqual(instance_conf['source'], 'instance_mock')
        field_kwargs = {'extra': 'value', 'foo': 'bar',
                        'view_name': 'bar-detail'}
        mock_adapter._generate_field.assert_called_with(
            mock_instance, mock_loc, '.ref', mock.ANY, False,
            **field_kwargs)

    def test_construct_drf_field(self):
        mock_loc = ('api', 'foo', '*', 'field', '.drf_field')
        mock_instance = {
            '.drf_field': {},
            '.foo': {},
        }
        all_constructors = {'.drf_field', '.foo'}
        mock_context = {'constructed': set(),
                        'all_constructors': all_constructors}
        mock_adapter = create_mock_object(
            DjangoRestAdapter, ['construct_drf_field'])
        self.assertRaises(doc.DeferConstructor,
                          mock_adapter.construct_drf_field, mock_adapter,
                          instance=mock_instance, spec={}, loc=mock_loc,
                          context=mock_context)
        mock_context['constructed'] = {'.foo'}

        mock_adapter.extract_type.return_value = None
        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.construct_drf_field, mock_adapter,
                          instance=mock_instance, spec={}, loc=mock_loc,
                          context=mock_context)

        mock_adapter.extract_type.return_value = '.identity'
        mock_adapter.construct_identity_field.return_value = 'identity field'
        mock_adapter.default_field_constructor.return_value = 'drf field'

        instance = mock_adapter.construct_drf_field(
            mock_adapter, instance=mock_instance, spec={}, loc=mock_loc,
            context=mock_context)
        self.assertEqual(instance, 'identity field')
        mock_adapter.construct_identity_field.assert_called_once_with(
            mock_instance, {}, mock_loc, mock_context, '.identity')
        mock_adapter.default_field_constructor.assert_not_called

        mock_adapter.extract_type.return_value = '.foo'
        instance = mock_adapter.construct_drf_field(
            mock_adapter, instance=mock_instance, spec={}, loc=mock_loc,
            context=mock_context)
        self.assertEqual(instance, 'drf field')
        mock_adapter.default_field_constructor.assert_called_once_with(
            mock_instance, {}, mock_loc, mock_context, '.foo')

    def test_construct_property(self):
        mock_properties = {
            'foo': 'foo_mapping',
            'bar': 'bar_mapping',
        }
        mock_adapter = create_mock_object(
            DjangoRestAdapter, ['construct_property', 'ADAPTER_CONF'])
        mock_adapter.PROPERTY_MAPPING = mock_properties
        mock_instance = {self.adapter_conf: {}}
        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.construct_property, mock_adapter,
                          instance=mock_instance, spec={}, loc=(),
                          context={}, property_name='unknown')

        instance = mock_adapter.construct_property(
            mock_adapter, instance=mock_instance, spec={},
            loc=(), context={}, property_name='foo')
        self.assertEqual(len(instance), 1)
        instance_conf = instance.get(mock_adapter.ADAPTER_CONF)
        self.assertEqual(len(instance_conf), 1)
        self.assertTrue(instance_conf['foo_mapping'])

    def test_validate_model_field(self):
        mock_adapter = create_mock_object(
            DjangoRestAdapter, ['validate_model_field', 'ADAPTER_CONF'])
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
                          None, 'foo', self.loc, field_type, None)
        mock_meta.get_field.assert_not_called

        source = 'myvalue'
        mock_adapter.extract_model.return_value = mock_model
        mock_adapter.validate_model_field(mock_adapter, None, 'foo', self.loc,
                                          field_type, source)
        mock_meta.get_field.assert_called_once_with(source)

        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.validate_model_field,
                          mock_adapter, None, 'foo', self.loc, mock_cls2,
                          source)

    def test_get_constructor_params(self):
        mock_structures = {
            'a': 'b',
            'b': 'a',
            '.collection': '.collection'
        }
        mock_model = mock.Mock()
        models = {'key': mock_model}
        self.adapter.STRUCTURES = mock_structures
        self.adapter.models = models
        mock_spec = {
            'key': {
                '.collection': {'a1': 'va1'},
                'key1': {
                    'b': {'b1': 'vb1', 'source': 'foo'},
                    'a': {'a2': 'va2'},
                    'key2': {
                        'key3': {
                            'b': {'b2': 'vb2'},
                            'one_more': {},
                        }
                    }
                }
            }
        }
        loc = ('key', 'key1', 'key2', 'key3', 'one_more')
        output = self.adapter.get_constructor_params(mock_spec, loc, [])
        self.assertEqual(len(output), 4)
        self.assertEqual(output[0], ('b', {'source': 'key3'}))
        self.assertEqual(output[1], ('a', {'source': 'foo'}))
        self.assertEqual(output[2], ('b', {'source': 'key1'}))
        self.assertEqual(output[3], ('.collection', {'model': mock_model}))

    def test_extract_related_model(self):
        output = mock.Mock(related_model=None)
        mock_meta = mock.Mock()
        mock_meta.get_field.return_value = output
        mock_model = mock.Mock(_meta=mock_meta)
        mock_adapter = create_mock_object(
            DjangoRestAdapter, ['extract_related_model', 'ADAPTER_CONF'])
        mock_adapter.extract_model.return_value = mock_model
        self.assertRaises(utils.DRFAdapterException,
                          mock_adapter.extract_related_model,
                          mock_adapter, None, None)

        output = mock.Mock(related_model='value')
        mock_meta.get_field.return_value = output
        output = mock_adapter.extract_related_model(
            mock_adapter, None, None)
        self.assertEqual(output, 'value')

    @mock.patch.object(utils, 'import_object')
    def test_get_or_import_model(self, mock_import):
        side_effect = lambda x: x + '_imported'
        mock_import.side_effect = side_effect
        spec = {
            'foo': {
                'model': 'a',
            },
            'bar': {
                'model': 'b'
            }
        }
        self.assertEqual(self.adapter.models, {})
        model = self.adapter._get_or_import_model(
            'foo', ('foo', 'model'), spec)
        self.assertEqual(model, 'a_imported')
        self.assertEqual(self.adapter.models, {'foo': 'a_imported'})
        mock_import.assert_called_once_with('a')

        model = self.adapter._get_or_import_model(
            'foo', ('foo', 'model'), spec)
        self.assertEqual(model, 'a_imported')
        self.assertEqual(self.adapter.models, {'foo': 'a_imported'})
        self.assertEqual(mock_import.call_count, 1)

        model = self.adapter._get_or_import_model(
            'bar', ('bar', 'model'), spec)
        self.assertEqual(model, 'b_imported')
        self.assertEqual(self.adapter.models,
                         {'foo': 'a_imported', 'bar': 'b_imported'})
        mock_import.assert_called_with('b')
        self.assertEqual(mock_import.call_count, 2)

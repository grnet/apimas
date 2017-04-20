import mock
import unittest
from apimas import documents as doc
from apimas.errors import InvalidSpec
from apimas.adapters.cookbooks import NaiveAdapter
from apimas.testing.helpers import create_mock_object


class TestNaiveAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = NaiveAdapter()

    def test_get_structural_elements(self):
        instance = {'.a': {}, 'b': {}, 'c': {}}
        elements = self.adapter.get_structural_elements(instance)
        self.assertEqual(len(elements), 2)
        self.assertTrue('b' in elements)
        self.assertTrue('c' in elements)

        instance = {'.a': {}, '.b': {}, '.c': {}}
        self.assertEqual(self.adapter.get_structural_elements(instance), [])

    def test_construct_collection(self):
        instance = {}
        self.assertRaises(AssertionError, self.adapter.construct_collection,
                          instance=instance, spec={}, loc=(), context={})

        loc = ('api', 'foo', '.collection')
        self.assertRaises(InvalidSpec,
                          self.adapter.construct_collection,
                          instance=instance, spec={}, loc=loc, context={})

        instance = {
            '*': {
                '.foo': {},
                '.bar': {},
            }
        }
        output = self.adapter.construct_collection(
            instance=instance, spec={}, loc=loc, context={})
        self.assertEqual(instance, output)

    def test_construct_type(self):
        type_mapping = {'foo': 1}
        self.adapter.TYPE_MAPPING = type_mapping

        self.assertRaises(InvalidSpec, self.adapter.construct_type,
                          instance={}, spec={}, loc=(), context={},
                          field_type='unknown')

        output = self.adapter.construct_type(
            instance={}, spec={}, loc=(), context={}, field_type='foo')
        self.assertEqual(len(output), 1)
        self.assertEqual(output[self.adapter.ADAPTER_CONF],
                         {'type': 1})

    def test_validate_structure(self):
        loc = ('foo', 'bar')
        self.assertRaises(InvalidSpec,
                          self.adapter.validate_structure,
                          instance={}, spec={}, loc=loc, context={})
        spec = {'a': {}, 'b': 1}
        self.assertRaises(InvalidSpec,
                          self.adapter.validate_structure,
                          instance={}, spec=spec, loc=loc, context={})
        spec['b'] = {'foo': 'bar'}
        self.adapter.validate_structure(instance={}, spec=spec, loc=loc,
                                        context={})

    def test_construct_ref(self):
        mock_adapter = create_mock_object(
            NaiveAdapter, ['construct_ref'])
        mock_instance = {'a': {}, 'b': {}}
        top_spec = {'api': {'foo': {}, 'bar': {}}}
        context = {'top_spec': top_spec}
        spec = {'to': 'unknown'}
        mock_loc = ('api', 'bar')

        self.assertRaises(InvalidSpec, mock_adapter.construct_ref,
                          mock_adapter, instance=mock_instance, spec={},
                          loc=mock_loc, context=context)
        mock_adapter.construct_type.assert_not_called

        spec['to'] = 'api/unknown'
        self.assertRaises(InvalidSpec, mock_adapter.construct_ref,
                          mock_adapter, instance=mock_instance, spec=spec,
                          loc=mock_loc, context=context)
        mock_adapter.construct_type.assert_not_called

        spec['to'] = 'api/foo'
        mock_adapter.construct_ref(mock_adapter, instance=mock_instance,
                                   spec=spec, loc=mock_loc, context=context)
        mock_adapter.construct_type.assert_called_once_with(
            mock_instance, spec, mock_loc, context, 'ref')

    def test_construct_identity(self):
        mock_properties = {'foo', 'bar', '.readonly'}
        self.adapter.PROPERTIES = mock_properties
        mock_loc = ('foo', 'bar')
        context = {'all_constructors': ['foo', 'bar']}
        self.assertRaises(InvalidSpec,
                          self.adapter.construct_identity,
                          instance={}, spec={}, loc=mock_loc, context=context)

        context = {'all_constructors': ['foo', '.readonly']}
        self.assertRaises(InvalidSpec,
                          self.adapter.construct_identity,
                          instance={}, spec={}, loc=mock_loc, context=context)

        context = {'all_constructors': ['.readonly']}
        output = self.adapter.construct_identity(
            instance={}, spec={}, loc=mock_loc, context=context)
        self.assertEqual(output, {})

        context = {'all_constructors': ['non_property']}
        output = self.adapter.construct_identity(
            instance={}, spec={}, loc=mock_loc, context=context)
        self.assertEqual(output, {})

    def test_construct_choices(self):
        mock_adapter = create_mock_object(NaiveAdapter, ['construct_choices'])

        # Case A: Parameter `allowed` not specified.
        self.assertRaises(InvalidSpec,
                          mock_adapter.construct_choices, mock_adapter,
                          instance={}, spec={}, loc=(), context=())
        mock_adapter.construct_type.assert_not_called

        # Case B: Parameter `allowed` specified but it is invalid.
        self.assertRaises(InvalidSpec,
                          mock_adapter.construct_choices, mock_adapter,
                          instance={}, spec={'allowed': 'invalid'}, loc=(),
                          context={})
        mock_adapter.construct_type.assert_not_called

        # Case C: Construction succeedeed
        instance = mock_adapter.construct_choices(
            mock_adapter, instance={}, spec={'allowed': ['foo', 'bar']},
            loc=(), context={})
        mock_adapter.construct_type.assert_called_once_with(
            {}, {'allowed': ['foo', 'bar']}, (), {}, 'choices')
        self.assertTrue(isinstance(instance, mock.Mock))

    def test_construct_property(self):
        mock_loc = ('foo', 'bar')
        mock_adapter = create_mock_object(
            NaiveAdapter, ['construct_property', 'ADAPTER_CONF'])
        mock_properties = {'a': 'b'}
        mock_adapter.PROPERTY_MAPPING = mock_properties
        mock_adapter.SKIP_FIELDS = {'bar'}
        mock_instance = {mock_adapter.ADAPTER_CONF: {}}
        context = {'constructed': ['foo', 'bar']}

        self.assertRaises(InvalidSpec,
                          mock_adapter.construct_property, mock_adapter,
                          instance=mock_instance, spec={}, loc=mock_loc,
                          context=context, property_name='unknown')

        mock_adapter.construct_type.return_value = 'test'
        self.assertRaises(doc.DeferConstructor,
                          mock_adapter.construct_property, mock_adapter,
                          instance=mock_instance, spec={}, loc=mock_loc,
                          context=context, property_name='a')

        mock_adapter.extract_type.return_value = 'bar'
        instance = mock_adapter.construct_property(
            mock_adapter, instance=mock_instance, spec={}, loc=mock_loc,
            context=context, property_name='a')
        self.assertEqual(instance, mock_instance)

        mock_adapter.extract_type.return_value = 'foo'
        instance = mock_adapter.construct_property(
            mock_adapter, instance=mock_instance, spec={}, loc=mock_loc,
            context=context, property_name='a')
        self.assertEqual(len(instance), 1)
        self.assertEqual(instance[mock_adapter.ADAPTER_CONF], {'b': True})

    def test_extract_type(self):
        mock_types = {'foo', 'bar'}
        self.adapter.TYPES = mock_types
        mock_instance = {
            'unknown': {}
        }
        self.assertIsNone(self.adapter.extract_type(mock_instance))

        mock_instance = {
            'foo': {},
        }
        self.assertEqual(self.adapter.extract_type(mock_instance), 'foo')

        mock_instance['bar'] = {}
        self.assertRaises(InvalidSpec, self.adapter.extract_type,
                          mock_instance)

    def test_init_adapter_conf(self):
        instance = {}
        output = self.adapter.init_adapter_conf(instance)
        self.assertEqual(len(output), 1)
        self.assertEqual(output[self.adapter.ADAPTER_CONF], {})

        instance = {self.adapter.ADAPTER_CONF: {}}
        output = self.adapter.init_adapter_conf(instance)
        self.assertEqual(output, instance)

        instance = {}
        output = self.adapter.init_adapter_conf(instance,
                                                initial={'foo': 'bar'})
        self.assertEqual(len(output), 1)
        self.assertEqual(output[self.adapter.ADAPTER_CONF], {'foo': 'bar'})

    def test_types(self):
        mock_instance = {'foo': {}, 'bar': {}}
        mock_loc = ('foo', 'bar')
        predicates = {
            'type': 'TYPES',
            'property': 'PROPERTIES',
        }
        for k, v in predicates.iteritems():
            with mock.patch.object(
                    self.adapter, 'construct_' + k,
                    autospec=True) as mock_func:
                mock_func.return_value = mock_instance
                for predicate_type in getattr(self.adapter, v):
                    # Fields with special handling.
                    if predicate_type in ['.identity', '.ref', '.choices']:
                        continue
                    func = getattr(
                        self.adapter, 'construct_' + predicate_type[1:])
                    self.assertEqual(
                        func(instance=mock_instance, spec=mock_instance,
                             loc=mock_loc, context={}), mock_instance)
                    mock_func.assert_called_with(
                        mock_instance, mock_instance, mock_loc, {},
                        predicate_type[1:])

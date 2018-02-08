import mock
import unittest
import docular as doc
from apimas.errors import InvalidSpec
from apimas.adapters.cookbooks import NaiveAdapter
from apimas.testing.helpers import (
    create_mock_object, create_mock_constructor_context)


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
        cons_kwargs = {}
        mock_context = create_mock_constructor_context(**cons_kwargs)

        self.assertRaises(AssertionError, self.adapter.construct_collection,
                          context=mock_context)

        cons_kwargs['loc'] = ('api', 'foo', '.collection')
        mock_context = create_mock_constructor_context(**cons_kwargs)
        self.assertRaises(InvalidSpec,
                          self.adapter.construct_collection,
                          context=mock_context)

        cons_kwargs['instance'] = {
            '*': {
                '.foo': {},
                '.bar': {},
            },
            self.adapter.ADAPTER_CONF: {}
        }
        mock_context = create_mock_constructor_context(**cons_kwargs)
        output = self.adapter.construct_collection(context=mock_context)
        self.assertEqual(mock_context.instance, output)

    def test_construct_type(self):
        type_mapping = {'foo': 1}
        self.adapter.TYPE_MAPPING = type_mapping

        mock_context = create_mock_constructor_context()

        self.assertRaises(InvalidSpec, self.adapter.construct_type,
                          context=mock_context,
                          field_type='unknown')

        output = self.adapter.construct_type(mock_context, field_type='foo')
        self.assertEqual(len(output), 1)
        self.assertEqual(output[self.adapter.ADAPTER_CONF],
                         {'type': 1})

    def test_validate_structure(self):
        mock_loc = ('foo', 'bar')
        mock_context = create_mock_constructor_context(
            loc=mock_loc)
        self.assertRaises(InvalidSpec,
                          self.adapter.validate_structure,
                          mock_context)

        mock_context.spec.update({'a': {}, 'b': 1})
        self.assertRaises(InvalidSpec,
                          self.adapter.validate_structure,
                          mock_context)

        mock_context.spec['b'] = {'foo': 'bar'}
        self.adapter.validate_structure(mock_context)

    def test_construct_ref(self):
        mock_adapter = create_mock_object(
            NaiveAdapter, ['construct_ref'])
        top_spec = {'api': {'foo': {}, 'bar': {}, 'a': {}, 'b': {}}}
        spec = {'to': 'unknown'}
        mock_loc = ('api', 'bar')
        mock_context = create_mock_constructor_context(
            top_spec=top_spec, spec=spec, loc=mock_loc)

        self.assertRaises(InvalidSpec, mock_adapter.construct_ref,
                          mock_adapter, context=mock_context)
        mock_adapter.construct_type.assert_not_called

        mock_context.spec['to'] = 'api/unknown'
        self.assertRaises(InvalidSpec, mock_adapter.construct_ref,
                          mock_adapter, context=mock_context)
        mock_adapter.construct_type.assert_not_called

        mock_context.spec['to'] = 'api/foo'
        mock_adapter.construct_ref(mock_adapter, context=mock_context)
        mock_adapter.construct_type.assert_called_once_with(
            mock_context, 'ref')

    def test_construct_identity(self):
        mock_properties = {'foo', 'bar', '.readonly'}
        self.adapter.PROPERTIES = mock_properties
        mock_loc = ('foo', 'bar')
        mock_context = create_mock_constructor_context(
            cons_siblings=['foo', 'bar'], loc=mock_loc)
        self.assertRaises(InvalidSpec,
                          self.adapter.construct_identity,
                          context=mock_context)

        mock_context = create_mock_constructor_context(
            cons_siblings=['foo', '.readonly'], loc=mock_loc)
        self.assertRaises(InvalidSpec,
                          self.adapter.construct_identity,
                          context=mock_context)

        mock_context = create_mock_constructor_context(
            cons_siblings=['.readonly'], loc=mock_loc)
        output = self.adapter.construct_identity(
            context=mock_context)
        self.assertEqual(output, {})

        mock_context = create_mock_constructor_context(
            loc=mock_loc, cons_siblings=['non property'])
        output = self.adapter.construct_identity(context=mock_context)
        self.assertEqual(output, {})

    def test_construct_choices(self):
        mock_adapter = create_mock_object(NaiveAdapter, ['construct_choices'])
        mock_context = create_mock_constructor_context()

        # Case A: Parameter `allowed` not specified.
        self.assertRaises(InvalidSpec,
                          mock_adapter.construct_choices, mock_adapter,
                          context=mock_context)
        mock_adapter.construct_type.assert_not_called

        mock_context = create_mock_constructor_context(
            spec={'allowed': 'invalid'})
        # Case B: Parameter `allowed` specified but it is invalid.
        self.assertRaises(InvalidSpec,
                          mock_adapter.construct_choices, mock_adapter,
                          context=mock_context)
        mock_adapter.construct_type.assert_not_called

        # Case C: Construction succeedeed
        mock_context =  create_mock_constructor_context(
            spec={'allowed': ['foo', 'bar']})
        instance = mock_adapter.construct_choices(
            mock_adapter, context=mock_context)
        mock_adapter.construct_type.assert_called_once_with(
            mock_context, 'choices')
        self.assertTrue(isinstance(instance, mock.Mock))

    def test_construct_property(self):
        mock_loc = ('foo', 'bar')
        mock_adapter = create_mock_object(
            NaiveAdapter, ['construct_property', 'ADAPTER_CONF'])
        mock_properties = {'a': 'b'}
        mock_adapter.PROPERTY_MAPPING = mock_properties
        mock_adapter.SKIP_FIELDS = {'bar'}
        mock_instance = {mock_adapter.ADAPTER_CONF: {}}

        mock_context = create_mock_constructor_context(
            instance=mock_instance,
            loc=mock_loc,
            constructed=['foo', 'bar'],
        )

        self.assertRaises(InvalidSpec,
                          mock_adapter.construct_property, mock_adapter,
                          context=mock_context, property_name='unknown')

        mock_adapter.construct_type.return_value = 'test'
        self.assertRaises(doc.DeferConstructor,
                          mock_adapter.construct_property, mock_adapter,
                          context=mock_context, property_name='a')

        mock_adapter.extract_type.return_value = 'bar'
        instance = mock_adapter.construct_property(
            mock_adapter, context=mock_context, property_name='a')
        self.assertEqual(instance, mock_context.instance)

        mock_adapter.extract_type.return_value = 'foo'
        instance = mock_adapter.construct_property(
            mock_adapter, context=mock_context, property_name='a')
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
        mock_context = create_mock_constructor_context(
            instance=mock_instance,
            loc=mock_loc,
        )

        def validate_call(predicate_type):
            func = getattr(
                self.adapter, 'construct_' + predicate_type[1:])
            self.assertEqual(
                func(context=mock_context), mock_instance)
            mock_func.assert_called_with(
                mock_context, predicate_type[1:])

        for k, v in predicates.iteritems():
            with mock.patch.object(
                    self.adapter, 'construct_' + k,
                    autospec=True) as mock_func:
                mock_func.return_value = mock_instance
                for predicate_type in getattr(self.adapter, v):
                    # Fields with special handling.
                    if predicate_type in ['.identity', '.ref', '.choices']:
                        continue
                    if predicate_type in ['.struct', '.structarray']:
                        with mock.patch.object(
                            self.adapter, 'validate_structure',
                            autospec=True):
                            validate_call(predicate_type)
                    else:
                        validate_call(predicate_type)

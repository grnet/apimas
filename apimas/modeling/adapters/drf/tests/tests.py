import mock
import unittest
from apimas.modeling.adapters.drf import utils
from apimas.modeling.adapters.drf import serializers
from apimas.modeling.adapters.drf.serializers import (
    get_paths, validate, generate, ApimasSerializer)


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

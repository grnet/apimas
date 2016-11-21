import mock
import unittest
from apimas.modeling.adapters.drf import utils
from apimas.modeling.adapters.drf import serializers
from apimas.modeling.adapters.drf.serializers import (
    get_paths, validate)


class TestSerializers(unittest.TestCase):

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
        mock_meta = mock.Mock()
        mock_model = mock.Mock(_meta=mock_meta)
        self.assertRaises(utils.DRFAdapterException, validate, mock_model,
                          field_properties)

        field_properties['field1']['prop_a'] = False
        validate(mock_model, field_properties)

        mock_field = mock.Mock()
        mock_field.get_internal_type.return_value = 'non_string'
        mock_meta.get_field.return_value = mock_field
        field_properties['field1']['allow_blank'] = True
        self.assertRaises(utils.DRFAdapterException, validate, mock_model,
                          field_properties)

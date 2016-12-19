import mock
import unittest
from apimas.modeling.adapters.drf.serializers import get_paths


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
        self.assertEqual(set(paths), {'field1', 'field2'})

        nested_fields = {'field': mock_sera}
        mock_serb = mock.MagicMock(fields=nested_fields)
        paths = get_paths(mock_serb.fields)
        self.assertEqual(set(paths), {'field/field1', 'field/field2'})

        # Test a 3-level serializer
        nested_fields = {'field1': 'a value', 'nested': mock_serb}
        mock_serc = mock.MagicMock(child=nested_fields)
        paths = get_paths(mock_serc.child)
        self.assertEqual(set(paths),
                         {'field1', 'nested/field/field1',
                          'nested/field/field2'})

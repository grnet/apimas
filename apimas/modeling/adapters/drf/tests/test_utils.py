import mock
import unittest
from apimas.modeling.adapters.drf import utils


class TestUtils(unittest.TestCase):

    @mock.patch.object(utils, 'get_package_module')
    def test_import_object(self, mock_func):
        self.assertRaises(utils.DRFAdapterException,
                          utils.import_object, None)
        self.assertRaises(utils.DRFAdapterException,
                          utils.import_object, 'module')
        mock_func.assert_not_called

        mock_func.side_effect = ImportError()
        self.assertRaises(utils.DRFAdapterException,
                          utils.import_object, 'module.object')
        mock_func.assert_called_with('module', raise_exception=True)

        mock_func.side_effect = None
        mock_module = mock.MagicMock(object=None)
        mock_func.return_value = mock_module
        self.assertRaises(utils.DRFAdapterException,
                          utils.import_object, 'module.object')

        mock_module = mock.MagicMock(object='foo')
        mock_func.return_value = mock_module
        self.assertEqual(utils.import_object('module.object'), 'foo')

    @mock.patch('importlib.import_module')
    def test_get_package_module(self, mock_func):
        mock_func.side_effect = ImportError()
        self.assertIsNone(utils.get_package_module('module'))
        mock_func.assert_called_once_with('module')

        self.assertRaises(ImportError, utils.get_package_module, 'module',
                          raise_exception=True)
        self.assertEqual(mock_func.call_count, 2)
        mock_func.assert_called_with('module')

        mock_func.side_effect = None
        mock_func.return_value = 'foo'
        self.assertEqual(utils.get_package_module('module'), 'foo')
        self.assertEqual(mock_func.call_count, 3)
        mock_func.assert_called_with('module')

import unittest
import mock
from apimas.adapters import Adapter


class TestAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = Adapter()

    def test_construct(self):
        self.assertRaises(NotImplementedError, self.adapter.construct, {})

    @mock.patch('apimas.adapters.utils.default_constructor')
    def test_get_constructors(self, mock_constructor):
        mock_method = mock.Mock()
        predicates = {'.foo', '.bar'}
        self.adapter.PREDICATES = predicates
        self.adapter.CONSTRUCTOR_PREFIX = 'mock'
        setattr(self.adapter, 'mock_bar', mock_method)
        mock_constructor.return_value = 'test'
        constructors = self.adapter.get_constructors()
        self.assertEqual(len(constructors), 2)
        self.assertEqual(constructors['bar'], mock_method)
        self.assertEqual(constructors['foo'], 'test')

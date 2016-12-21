import unittest
from apimas.modeling.adapters import utils


class TestUtils(unittest.TestCase):
    def test_default_constructor(self):
        predicate = '.mock'
        func = utils.default_constructor(predicate)
        self.assertRaises(NotImplementedError, func, instance={}, spec={},
                          loc=(), context={})

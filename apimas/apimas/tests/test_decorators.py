import unittest
import mock
from apimas.decorators import after, last
from apimas.errors import InvalidInput
from apimas.documents import DeferConstructor


class TestDecorators(unittest.TestCase):
    def test_after(self):
        mock_function = mock.MagicMock(__name__='foo')
        context = {
            'all_constructors': ['x', 'y', 'z'],
            'constructed': []
        }

        # Case A: Invalid constructors types.
        self.assertRaises(InvalidInput, after, 'y')
        mock_function.assert_not_called

        # Case B: Defer construction.
        decorated_func = after(['y'])(mock_function)
        self.assertRaises(DeferConstructor, decorated_func,
                          context=context)
        mock_function.assert_not_called

        # Case C: Decorated function runs successfully.
        decorated_func = after(['y', 'k'])(mock_function)
        context['constructed'] = ['y']
        decorated_func(context=context)
        mock_function.assert_called_once_with(context=context)

    def test_last(self):
        constructors = ['x', 'y', 'z']
        context = {
            'all_constructors': constructors,
            'constructed': []
        }
        mock_function = mock.MagicMock(__name__='foo')
        decorated_func = last(mock_function)
        for con in constructors[:-1]:
            self.assertRaises(DeferConstructor, decorated_func,
                              context=context)
            mock_function.assert_not_called
            context['constructed'].append(con)

        decorated_func(context=context)
        mock_function.assert_called_once_with(context=context)

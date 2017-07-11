import unittest
import warnings
import mock
from apimas.decorators import after, last, conditional
from apimas.errors import InvalidInput
from apimas.documents import DeferConstructor
from apimas.testing.helpers import create_mock_constructor_context


class TestDecorators(unittest.TestCase):
    def test_conditionals(self):
        mock_function = mock.MagicMock(__name__='foo')
        context = create_mock_constructor_context(
            cons_siblings=['x', 'y', 'z'],
            constructed=[]
        )
        # Case A: Invalid constructors types.
        self.assertRaises(InvalidInput, conditional, 'y')
        mock_function.assert_not_called

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Case B: Missing constructor given. Constructor does not run.
            decorated_func = conditional(['k'])(mock_function)
            decorated_func(context=context)
            mock_function.assert_not_called
            self.assertEqual(len(w), 1)

            # Case C: Decorated function runs successfully without warning.
            decorated_func = conditional(['y'])(mock_function)
            decorated_func(context=context)
            mock_function.assert_called_once_with(context=context)
            self.assertEqual(len(w), 1)

    def test_after(self):
        mock_function = mock.MagicMock(__name__='foo')
        context = create_mock_constructor_context(
            cons_siblings=['x', 'y', 'z'],
            constructed=[]
        )

        # Case A: Invalid constructors types.
        self.assertRaises(InvalidInput, after, 'y')
        mock_function.assert_not_called

        # Case B: Defer construction.
        decorated_func = after(['y'])(mock_function)
        self.assertRaises(DeferConstructor, decorated_func,
                          context=context)
        mock_function.assert_not_called

        # Case C: A invalid constructor, i.e. 'k'.
        decorated_func = after(['k'])(mock_function)
        context.constructed.append('y')
        self.assertRaises(InvalidInput, decorated_func,
                          context=context)
        mock_function.assert_not_called

        # Case D: Decorated function runs successfully.
        decorated_func = after(['y'])(mock_function)
        decorated_func(context=context)
        mock_function.assert_called_once_with(context=context)

    def test_last(self):
        constructors = ['x', 'y', 'z']
        context = create_mock_constructor_context(
            cons_siblings=constructors,
            constructed=[]
        )
        mock_function = mock.MagicMock(__name__='foo')
        decorated_func = last(mock_function)
        for con in constructors[:-1]:
            self.assertRaises(DeferConstructor, decorated_func,
                              context=context)
            mock_function.assert_not_called
            context.constructed.append(con)

        decorated_func(context=context)
        mock_function.assert_called_once_with(context=context)

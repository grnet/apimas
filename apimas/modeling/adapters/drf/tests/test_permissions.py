import unittest
import mock
from django.contrib.auth.models import AnonymousUser
from apimas.modeling.core import documents as doc
from apimas.modeling.tests.helpers import create_mock_object
from apimas.modeling.adapters.drf.permissions import ApimasPermissions
from apimas.modeling.permissions.tabmatch import Tabmatch


class TestPermissions(unittest.TestCase):
    def setUp(self):
        self.mock_request = mock.MagicMock()
        self.mock_view = mock.MagicMock()
        self.mock_view.action = 'mock'

    def test_get_pattern_sets(self):
        mock_user = mock.MagicMock(spec=AnonymousUser)
        mock_permission = create_mock_object(
            ApimasPermissions, ['get_pattern_sets', 'ANONYMOUS_ROLES'])
        self.mock_request.user = mock_user
        pattern_set = mock_permission.get_pattern_sets(
            mock_permission, self.mock_request, self.mock_view)
        self.assertEqual(len(pattern_set), 4)
        self.assertEqual(pattern_set[0], ['mock'])
        self.assertEqual(pattern_set[1], mock_permission.ANONYMOUS_ROLES)
        self.assertEqual(pattern_set[2], [doc.ANY])
        self.assertEqual(pattern_set[3], [doc.ANY])

        mock_user = mock.MagicMock()
        mock_user.apimas_roles = ['my roles']
        self.mock_request.user = mock_user
        pattern_set = mock_permission.get_pattern_sets(
            mock_permission, self.mock_request, self.mock_view)
        self.assertEqual(len(pattern_set), 4)
        self.assertEqual(pattern_set[0], ['mock'])
        self.assertEqual(pattern_set[1], ['my roles'])
        self.assertEqual(pattern_set[2], [doc.ANY])
        self.assertEqual(pattern_set[3], [doc.ANY])

    def test_isallowed(self):
        mock_tabmatch = mock.Mock(spec=Tabmatch)
        mock_tabmatch.multimatch.return_value = []
        mock_permissions = create_mock_object(
            ApimasPermissions, ['isallowed'])
        mock_permissions.permissions = mock_tabmatch
        pattern_set = [['foo'], ['bar'], [doc.ANY], [doc.ANY]]
        mock_permissions.get_pattern_sets.return_value = pattern_set

        # Case A: No matches.
        allowed = mock_permissions.isallowed(
            mock_permissions, self.mock_request, self.mock_view, obj=None)
        self.assertFalse(allowed)
        mock_permissions.check_field_conditions.assert_not_called

        # Case B: There are matches, but invalid states.
        matches = [mock.Mock(field=doc.ANY, state='bar'),
                   mock.Mock(field='foo', state='foo')]
        mock_tabmatch.multimatch.return_value = matches
        mock_states = {
            'foo': False,
            'bar': False,
        }
        mock_permissions.check_state_conditions.return_value = mock_states
        allowed = mock_permissions.isallowed(
            mock_permissions, self.mock_request, self.mock_view, obj=None)
        self.assertFalse(allowed)
        mock_permissions.check_state_conditions.assert_called_once_with(
            self.mock_request, self.mock_view, matches, None)

        # Case C: There are some states which are valid.
        mock_states = {
            'foo': True,
            'bar': False,
        }
        mock_permissions.check_state_conditions.return_value = mock_states
        allowed = mock_permissions.isallowed(
            mock_permissions, self.mock_request, self.mock_view, obj=None)
        self.assertTrue(allowed)
        mock_permissions.check_state_conditions.assert_called_with(
            self.mock_request, self.mock_view, matches, None)
        mock_permissions.check_field_conditions.assert_called_once_with(
            self.mock_request, self.mock_view, matches[1:])

    def test_has_permission(self):
        lookup_field = 'foo'
        kwargs = {'foo': 'bar'}
        mock_permissions = create_mock_object(
            ApimasPermissions, ['has_permission'])
        self.mock_view.lookup_field = lookup_field
        self.mock_view.kwargs = kwargs

        self.assertTrue(mock_permissions.has_permission(
            mock_permissions, self.mock_request, self.mock_view))
        mock_permissions.isallowed.assert_not_called

        self.mock_view.kwargs = {}
        output = mock_permissions.has_permission(
            mock_permissions, self.mock_request, self.mock_view)
        self.assertTrue(isinstance(output, mock.Mock))
        mock_permissions.isallowed.assert_called_once_with(
            self.mock_request, self.mock_view)

    def test_set_field_context(self):
        matches_a = [doc.ANY, 'foo']
        matches_b = ['bar']
        match_patterns = [matches_a, matches_b]
        mock_permission = create_mock_object(
            ApimasPermissions, ['set_field_context'])
        self.mock_request.parser_context = {}
        expected = [doc.ANY, ['bar']]
        for i, match_pattern in enumerate(match_patterns):
            mock_permission.set_field_context(
                mock_permission, self.mock_request, self.mock_view,
                match_pattern)
            accessible_fields = self.mock_request.parser_context.get(
                'accesible_fields')
            writable_fields = self.mock_request.parser_context.get(
                'writable_fields')
            self.assertEqual(writable_fields, expected[i])
            self.assertIsNone(accessible_fields)
        self.mock_request.parser_context = {}
        for action in ['list', 'retrieve']:
            self.mock_view.action = action
            for i, match_pattern in enumerate(match_patterns):
                mock_permission.set_field_context(
                    mock_permission, self.mock_request, self.mock_view,
                    match_pattern)
                accessible_fields = self.mock_request.parser_context.get(
                    'accesible_fields')
                writable_fields = self.mock_request.parser_context.get(
                    'writable_fields')
                self.assertEqual(accessible_fields, expected[i])
                self.assertIsNone(writable_fields)

    def test_allowed_fields(self):
        matches = [mock.Mock(field=doc.ANY), mock.Mock(field='b/c')]
        data = {
            'a': 1,
            'b': {
                'foo': {
                    'bar': 1
                },
                'c': 1,
            }
        }
        self.mock_request.data = data
        mock_permission = create_mock_object(
            ApimasPermissions, ['allowed_fields'])
        allowed_fields = mock_permission.allowed_fields(
            mock_permission, self.mock_request, self.mock_view, matches)
        self.assertEqual(allowed_fields, {'b/c', doc.ANY})

        for action in ['list', 'retrieve']:
            self.mock_view.action = action
            allowed_fields = mock_permission.allowed_fields(
                mock_permission, self.mock_request, self.mock_view, matches)
            self.assertEqual(allowed_fields, {'b/c', doc.ANY})

    def test_check_state_conditions(self):
        mock_model = mock.MagicMock()
        mock_model.collection_foo.return_value = False
        mock_model.object_foo.return_value = False
        matches = [mock.Mock(state='foo'), mock.Mock(state='foo')]
        mock_permission = create_mock_object(
            ApimasPermissions, ['check_state_conditions'])
        mock_permission.COLLECTION_CHECK_PREFIX = 'collection'
        mock_permission.OBJECT_CHECK_PREFIX = 'object'
        mock_permission.model = mock_model
        self.assertEqual(mock_permission.check_state_conditions(
            mock_permission, self.mock_request, self.mock_view,
            matches, obj=None), {'foo': False})
        mock_model.collection_foo.assert_called_once

        matches = [mock.Mock(state=doc.ANY), mock.Mock(state='foo')]
        self.assertEqual(mock_permission.check_state_conditions(
            mock_permission, self.mock_request, self.mock_view,
            matches, obj=None), {doc.ANY: True, 'foo': False})

        mock_row = mock.Mock(state='foo')
        matches = [mock_row]
        for ret in [True, False]:
            for obj in [None, 'test']:
                if obj is None:
                    mock_model.collection_foo.return_value = ret
                else:
                    mock_model.object_foo.return_value = ret
                states = mock_permission.check_state_conditions(
                    mock_permission, self.mock_request, self.mock_view,
                    matches, obj)
                self.assertEqual(states, {'foo': ret})
                if obj is None:
                    mock_model.collection_foo.assert_called_with(
                        row=mock_row, request=self.mock_request,
                        view=self.mock_view)
                else:
                    mock_model.object_foo.assert_called_with(
                        obj, row=mock_row, request=self.mock_request,
                        view=self.mock_view)

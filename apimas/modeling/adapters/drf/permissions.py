from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import BasePermission
from apimas.modeling.core.exceptions import ApimasException
from apimas.modeling.core.documents import ANY, AnyPattern, doc_to_ns
from apimas.modeling.permissions.tabmatch import Tabmatch


class ApimasPermissions(BasePermission):
    COLLECTION_CHECK_PREFIX = 'check_collection_state'
    OBJECT_CHECK_PREFIX = 'check_resource_state'

    message = None
    COLUMNS = ('action', 'role', 'field', 'state', 'comment')

    ANONYMOUS_ROLES = ['anonymous']

    def __init__(self, rules, model):
        self.permissions = Tabmatch(self.COLUMNS)
        self.permissions.update(
            map((lambda x: self.permissions.Row(*x)), rules))
        self.model = model

    def get_pattern_sets(self, request, view):
        """
        Get all patterns sets from request's context.

        Specifically, get groups to which use belongs, and action of request.
        """
        action = view.action
        if isinstance(request.user, AnonymousUser):
            roles = self.ANONYMOUS_ROLES
        else:
            roles = getattr(request.user, 'apimas_roles', None)
            if roles is None:
                raise ApimasException(
                    'Cannot find propety `apimas_roles` on `user` object')
        return [[action], roles, [ANY], [ANY]]

    def isallowed(self, request, view, obj=None):
        """
        Method to check if requested user has permission to perform an action
        to a collection or a resource level.

        It actually matches the request context, i.e. action, groups, fields,
        state with the already defined permission rules.

        It marks which fields are accessible or writable so that serializer
        can handle data accordingly afterwards.
        """
        pattern_set = self.get_pattern_sets(request, view)
        expand_columns = {'field', 'state'}
        matches = list(
            self.permissions.multimatch(pattern_set, expand=expand_columns))
        if not matches:
            return False

        # We check which matching states are valid, and then we get the
        # subset of rules which match the valid states. If the is subset is
        # empty, then the permissions is not granted.
        state_conditions = self.check_state_conditions(request, view, matches,
                                                       obj)
        matches = filter((lambda x: state_conditions[x.state]), matches)
        if not matches:
            return False
        self.check_field_conditions(request, view, matches)
        return True

    def set_field_context(self, request, view, fields):
        """
        This method marks which fields are accesible or writable based on
        the given request context.
        """
        key = 'accesible_fields' if view.action in ['list', 'retrieve']\
            else 'writable_fields'
        if any(isinstance(field, AnyPattern) for field in fields):
            request.parser_context[key] = ANY
        else:
            request.parser_context[key] = fields

    def has_permission(self, request, view):
        """
        Method to check if a user has a permission to perform an action on
        a collection level.

        It triggers two checks. One check is associated with the fields
        included in this request and the last check is related to the state.

        The check of the state triggers a callable bound to the db model of
        the resource.
        """
        if view.lookup_field in view.kwargs:
            return True
        return self.isallowed(request, view)

    def has_object_permission(self, request, view, obj):
        """
        Method to check if a user has a permission to perform actions on a
        resource level.

        It checks the state of the instance according to a callable bound
        to the db model of the resource..
        """
        return self.isallowed(request, view, obj)

    def allowed_fields(self, request, view, matches):
        """
        This method determines which fields are allowed given the matches
        of permission rules.

        In case there are data included in the request, then this method
        returns the intersectional items of matching rules and included
        fields.
        """
        allowed_keys = {row.field for row in matches}
        if view.action in ['list', 'retrieve']:
            return allowed_keys
        fields = set(doc_to_ns(dict(request.data)).keys())
        allowed_keys = set()
        for row in matches:
            if isinstance(row.field, AnyPattern):
                allowed_keys.add(row.field)
            if row.field in fields:
                allowed_keys.add(row.field)
        return allowed_keys

    def check_field_conditions(self, request, view, matches):
        """
        This method marks which fields are accessible or writable so that
        serializer can handle data accordingly afterwards.
        """
        fields = self.allowed_fields(request, view, matches)
        self.set_field_context(request, view, fields)

    def check_state_conditions(self, request, view, matches, obj=None):
        """
        For the states that match to the pattern sets, this function checks
        which states are statisfied.

        Subsequently, it returns a dictionary which maps each state with
        its satisfiability (`True` or `False`).
        """
        state_conditions = {}
        for row in matches:
            if isinstance(row.state, AnyPattern):
                state_conditions[row.state] = True
            if row.state in state_conditions:
                continue
            prefix = self.OBJECT_CHECK_PREFIX if obj is not None\
                else self.COLLECTION_CHECK_PREFIX
            method_name = prefix + '_' + row.state
            method = getattr(self.model, method_name, None)
            if callable(method):
                kwargs = {
                    'row': row,
                    'request': request,
                    'view': view,
                }
                access_ok = method(obj, **kwargs) if obj is not None\
                    else method(**kwargs)
                state_conditions[row.state] = access_ok
        return state_conditions

    def __call__(self):
        return self

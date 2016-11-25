from rest_framework.permissions import BasePermission
from apimas.modeling.core.exceptions import ApimasException
from apimas.modeling.core.documents import ANY, AnyPattern, doc_to_ns
from apimas.modeling.permissions.tabmatch import Tabmatch


class ApimasPermissions(BasePermission):
    COLLECTION_CHECK_PREFIX = 'check_collection_state'
    OBJECT_CHECK_PREFIX = 'check_resource_state'

    message = None

    def __init__(self, rules, model):
        self.permissions = Tabmatch(
            ('action', 'role', 'field', 'state', 'comment'))
        self.permissions.update(
            map((lambda x: self.permissions.Row(*x)), rules))
        self.model = model

    def get_pattern_sets(self, request, view):
        """
        Get all patterns sets from request's context.

        Specifically, get groups to which use belongs, and action of request.
        """
        action = view.action
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
        self.check_field_conditions(request, view, matches)
        return self.check_state_conditions(request, view, matches, obj)

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

    def check_field_conditions(self, request, view, matches):
        """
        This method marks which fields are accessible or writable so that
        serializer can handle data accordingly afterwards.
        """
        fields = set(doc_to_ns(dict(request.data)).keys())
        allowed_keys = set()
        for row in matches:
            if isinstance(row.field, AnyPattern):
                return True
            allowed_keys.add(row.field)
        if view.action in ['list', 'retrieve']:
            allowed_keys = ANY if ANY in allowed_keys else allowed_keys
            request.parser_context['permitted_fields'] = allowed_keys
            return
        request.parser_context['non_writable_fields'] = fields - allowed_keys

    def check_state_conditions(self, request, view, matches, obj=None):
        """
        For the states that match to the pattern sets, this function checks
        if this state is statisfied.

        If any matched state is statisfied then, the permission is given.
        """
        for row in matches:
            if isinstance(row.state, AnyPattern):
                return True
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
                if access_ok:
                    return True
        return False

    def __call__(self):
        return self

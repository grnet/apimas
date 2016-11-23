from rest_framework.permissions import BasePermission
from apimas.modeling.core.documents import ANY, AnyPattern, doc_to_ns
from apimas.modeling.permissions.tabmatch import Tabmatch


class ApimasPermissions(BasePermission):
    COLLECTION_CHECK_PREFIX = 'check_collection_state'
    OBJECT_CHECK_PREFIX = 'check_resource_state'

    message = None

    def __init__(self, rules, model):
        self.permissions = Tabmatch(
            ('action', 'group', 'field', 'state', 'comment'))
        self.permissions.update(
            map((lambda x: self.permissions.Row(*x)), rules))
        self.model = model

    def get_pattern_sets(self, request, view):
        """
        Get all patterns sets from request's context.

        Specifically, get groups to which use belongs, and action of request.
        """
        action = view.action
        groups = map((lambda x: x.name), request.user.groups.all())
        return [[action], groups, [ANY], [ANY]]

    def has_permission(self, request, view):
        """
        Method to check if a user has a permission to perform an action on
        a collection level.

        It triggers two checks. One check is associated with the fields
        included in this request and the last check is related to the state.

        The check of the state triggers a callable bound to the db model of
        the resource.
        """
        pattern_set = self.get_pattern_sets(request, view)
        self.check_field_conditions(request, view, pattern_set)
        return self.check_state_conditions(request, view, pattern_set)

    def has_object_permission(self, request, view, obj):
        """
        Method to check if a user has a permission to perform actions on a
        resource level.

        It checks the state of the instance according to a callable bound
        to the db model of the resource..
        """
        pattern_set = self.get_pattern_sets(request, view)
        return self.check_state_conditions(request, view, pattern_set, obj=obj)

    def check_field_conditions(self, request, view, pattern_set):
        """
        Check that all fields that are included in this request match with
        the given rules.
        """
        fields = set(doc_to_ns(dict(request.data)).keys())
        matches = list(
            self.permissions.multimatch(pattern_set, expand={'field'}))
        allowed_keys = {x.field for x in matches}
        if view.action in ['list', 'retrieve']:
            allowed_keys = ANY if ANY in allowed_keys else allowed_keys
            request.parser_context['permitted_fields'] = allowed_keys
            return
        if ANY in allowed_keys:
            return
        request.parser_context['non_writable_fields'] = fields - allowed_keys

    def check_state_conditions(self, request, view, pattern_set, obj=None):
        """
        For the states that match to the pattern sets, this function checks
        if this state is statisfied.

        If any matched state is statisfied then, the permission is given.
        """
        matches = self.permissions.multimatch(pattern_set, expand={'state'})
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

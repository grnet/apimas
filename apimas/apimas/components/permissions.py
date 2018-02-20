import docular
from apimas.components import BaseProcessor, ProcessorConstruction
from apimas import documents as doc
from apimas import utils
from apimas.errors import AccessDeniedError, InvalidInput
from apimas.tabmatch import Tabmatch
from apimas.components.utils import expand_doc_keys, Singleton


Leaf = Singleton('Leaf')


def no_constructor(instance):
    pass

FIELD_SEPARATOR = '/'


_default_rules = []


def _is_prefixed(path, prefix=None):
    if prefix is None:
        return False
    prefix_len = len(prefix)
    return prefix_len < len(path) and path[:prefix_len] == prefix


def expand_paths(matched_fields, fields_spec):
    if matched_fields is doc.ANY:
        return expand_doc_keys(fields_spec)

    paths = set()
    prev = None
    for field in sorted(matched_fields):
        if _is_prefixed(field, prev):
            continue

        subspec = docular.doc_get(fields_spec, field)
        if subspec is None:
            raise InvalidInput(
                "illegal field '%s' in permission rules" % str(field))

        paths.update(expand_doc_keys(subspec, prefix=field))
        prev = field
    return paths


def get_matched_allowed_fields(matches):
    """
    Checks which fields are allowed to be modified or viewed based on
    matches.
    """
    allowed_keys = set()
    for row in matches:
        if isinstance(row.field, doc.AnyPattern):
            return doc.ANY
        allowed_keys.add(tuple(row.field.split(FIELD_SEPARATOR)))
    return allowed_keys


def mk_collection_path(loc):
    endpoint_prefix = loc[0]

    segments = []
    collections = loc[1:]
    for i, name in enumerate(reversed(collections)):
        position, is_fields = divmod(i, 2)
        if not is_fields:
            segments.append(name)
        else:
            assert name == 'fields'
    segments.append(endpoint_prefix)
    return '/'.join(reversed(segments))


def action_constructor(instance, loc):
    action_name = loc[-1]
    value = {}
    value['read_permissions'] = instance.get('read_permissions', action_name)
    value['write_permissions'] = instance.get('write_permissions', action_name)
    value['permissions_namespace'] = docular.doc_get(
        instance, 'permissions_namespace')
    docular.doc_spec_set(instance, value)


def make_fields_spec(instance):
    fields_spec = {}
    for key, value in docular.doc_spec_iter_values(instance['fields']):
        if value:
            value = value['fields_spec']
        else:
            value = Leaf
        fields_spec[key] = value
    return fields_spec


def collection_constructor(instance, loc, top_spec):
    value = {}
    value['permission_rules'] = docular.doc_spec_get(
        docular.doc_inherit2(top_spec, loc, ('.meta', 'permission_rules')))
    value['collection_path'] = mk_collection_path(loc)
    value['fields_spec'] = make_fields_spec(instance)
    docular.doc_spec_set(instance, value)


def struct_constructor(instance):
    value = {'fields_spec': make_fields_spec(instance)}
    docular.doc_spec_set(instance, value)


PERMISSIONS_CONSTRUCTORS = docular.doc_spec_init_constructor_registry(
    {'.field.collection.*': collection_constructor,
     '.field.struct': struct_constructor,
     '.action': action_constructor},
    default=no_constructor)


class PermissionsProcessor(BaseProcessor):
    """
    This processor handles the permissions in an application.

    Permissions are expressed with a set of rules. Each rule consists of:

        - `collection`: The name of the collection to which the rule is
          applied.
        - `action`: The name of the action for which the rule is valid.
        - `role`: The role of the user (entity who performs the request)
          who is authorized to make request calls.
        - `field`: The set of fields that are allowed to be handled in this
          request (either for writing or retrieval).
        - `state`: The state of the collection which **must** be valid when
          the request is performed.

    When a request is performed, we know about the collection, action, role,
    and field columns. This processor provides hooks to check the validity of
    the last column, i.e. `state`.

    Also, this processor saves which fields are allowed to be modified or
    viewed inside request context for later use from other processors.

    """

    READ_KEYS = {
        'user': 'auth/user',
        'instance': 'backend/instance',
    }

    WRITE_KEYS = (
        'permissions/can_read',
        'permissions/read_fields',
        'permissions/can_write',
        'permissions/write_fields',
    )

    COLUMNS = ('collection', 'action', 'role', 'field', 'state', 'comment')

    ANONYMOUS_ROLES = ['anonymous']

    def __init__(self, collection_loc, action_name,
                 permission_rules, collection_path, fields_spec,
                 read_permissions, write_permissions, permissions_namespace):

        rules_funcname = permission_rules
        rules = utils.import_object(rules_funcname)() if rules_funcname \
                else _default_rules

        self.fields_spec = fields_spec
        self.collection_path = collection_path
        self.action_name = action_name
        self.read_permissions_tag = read_permissions
        self.write_permissions_tag = write_permissions
        self.namespace = permissions_namespace

        self.tab_rules = self.init_tab_rules(rules)

    def _parse_rules(self, rules):
        """
        Parse given rules and construct the appropriate segment patterns.

        Example:
            '*' => doc.ANY
        """
        parsed_rules = []
        nu_columns = len(self.COLUMNS)
        for rule in rules:
            if len(rule) != nu_columns:
                msg = ('Rules must consist of {!s} columns. An invalid rule'
                       ' found ({!r})')
                raise InvalidInput(msg.format(nu_columns, ','.join(rule)))
            parsed_rules.append([doc.parse_pattern(segment)
                                for segment in rule])
        return parsed_rules

    def init_tab_rules(self, rules):
        rules = self._parse_rules(rules)
        tab_rules = Tabmatch(self.COLUMNS)
        tab_rules.update(
            map((lambda x: tab_rules.Row(*x)), rules))
        return tab_rules

    def _get_pattern_set(self, collection, action, user):
        """
        Get all patterns set from request's context.

        Specifically, get groups to which user belongs, and action of request.
        """
        if user is None:
            roles = self.ANONYMOUS_ROLES
        else:
            roles = getattr(user, 'apimas_roles', None)
            assert roles is not None, (
                'Cannot find property `apimas_roles` on `user` object')
        return [
                [collection],
                [action],
                roles,
                [doc.ANY],
                [doc.ANY],
                [doc.ANY],
        ]

    def check_state_conditions(self, matches, context, instance=None):
        """
        For the states that match to the pattern sets, this function checks
        which states are statisfied.

        Subsequently, it returns a dictionary which maps each state with
        its satisfiability (`True` or `False`).
        """
        state_conditions = {}
        for row in matches:
            # Initialize all states as False.
            if isinstance(row.state, doc.AnyPattern):
                state_conditions[row.state] = True
                continue

            # Avoid re-evaluation of state conditions.
            if row.state in state_conditions:
                continue
            state_conditions[row.state] = False

            prefix = '%s.' % self.namespace if self.namespace else ''
            state_funcname = prefix + row.state
            func = utils.import_object(state_funcname)

            if callable(func):
                kwargs = {'row': row, 'context': context}
                access_ok = (
                    func(instance, **kwargs)
                    if instance is not None
                    else func(**kwargs)
                )
                state_conditions[row.state] = access_ok
        return state_conditions

    def compute_permissions(
            self, collection, action_tag, user, instance, context):
        pattern_set = self._get_pattern_set(collection, action_tag, user)
        expand_columns = {'field', 'state'}
        matches = list(self.tab_rules.multimatch(
            pattern_set, expand=expand_columns))
        if not matches:
            return False, []

        # We check which matching states are valid, and then we get the
        # subset of rules which match the valid states. If the subset is
        # empty, then the permission is not granted.
        state_conditions = self.check_state_conditions(
            matches, context, instance=instance)
        matches = filter((lambda x: state_conditions[x.state]), matches)
        if not matches:
            return False, []

        # As a final step, we save in the context the list of fields that
        # are allowed to be read or written.
        allowed_fields = get_matched_allowed_fields(matches)
        expanded_fields = expand_paths(allowed_fields, self.fields_spec)
        return True, expanded_fields

    def process(self, collection, url, action, context):
        context_data = self.read(context)
        user = context_data.get('user')
        instance = context_data.get('instance')

        can_read, read_fields = self.compute_permissions(
            self.collection_path, self.read_permissions_tag,
            user, instance, context)
        if self.write_permissions_tag == self.read_permissions_tag:
            can_write, write_fields = can_read, read_fields
        else:
            can_write, write_fields = self.compute_permissions(
                self.collection_path, self.write_permissions_tag,
                user, instance, context)

        if not can_read and not can_write:
            raise AccessDeniedError(
                'You do not have permission to do this action')

        result = (can_read, read_fields, can_write, write_fields)
        self.write(result, context)


Permissions = ProcessorConstruction(
    PERMISSIONS_CONSTRUCTORS, PermissionsProcessor)

from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import FieldDoesNotExist
from django.db.models  import Model
from django.db.models.query import QuerySet
from apimas import documents as doc, utils
from apimas.errors import (AccessDeniedError, ConflictError, InvalidInput,
                           InvalidSpec)
from apimas.components import BaseProcessor
from apimas.tabmatch import Tabmatch
from apimas.django import utils as django_utils
from apimas.serializers import Date, DateTime, Integer, Float, Boolean, List
from apimas.constructors import Dummy, Object


REF = '.ref'
STRUCT = '.struct='
ARRAY_OF = '.array of='


class InstanceToDict(BaseProcessor):
    name = 'apimas.django.processors.InstanceToDict'

    READ_KEYS = {
        'instance': 'response/content',
        'model': 'store/orm_model',
        'allowed_fields': 'store/permissions/allowed_fields',
    }

    WRITE_KEYS = (
        'response/content',
    )

    def _extract_many(self, instance, field_name):
        """
        Extracts the value of a many to many or one to many django model
        relation.
        """
        try:
            return getattr(instance, field_name).all()
        except AttributeError:
            return getattr(instance, field_name + '_set').all()

    def _extract_rel_id(self, instance, field_name):
        """
        Extracts the id of a one to one or many to one django model
        relation.
        """
        try:
            return getattr(instance, field_name + '_id')
        except AttributeError:
            return getattr(instance, field_name)

    def _extract_rel(self, orm_model, instance, field, field_spec):
        """
        Helper function to get the python native format of a django
        related field.
        """
        many = field.many_to_many or field.one_to_many
        source = doc.doc_get(
            field_spec, ('.meta', 'source')) or field.name
        if many:
            value = self._extract_many(instance, source)
            if REF in field_spec[ARRAY_OF]:
                return [getattr(v, 'pk') for v in value]
            return [
                self.to_dict(
                    field.related_model, v,
                    field_spec[ARRAY_OF][STRUCT]
                ) for v in value
            ]
        if not hasattr(instance, field.name):
            return None
        if REF in field_spec:
            return self._extract_rel_id(instance, field.name)
        return self.to_dict(field.related_model, getattr(instance, source),
                            field_spec['.struct='])

    def to_dict(self, orm_model, instance, spec=None):
        """
        Constructs a given model instance a python dict.

        Only the model attributes which are declared on specification are
        included in the returned dictionary.

        Args:
            orm_model: Django model associated with the instance.
            instance: Model instance to be converted into a python dict.
            spec (dict): Specification of collection.

        Returns:
            dict: Dictionary format of a model instance.
        """
        if instance is None:
            return None
        spec_properties = spec or self.spec.get('*')
        data = {}
        for k, v in spec_properties.iteritems():
            # Ignore predicates.
            if k.startswith('.'):
                continue
            source = doc.doc_get(v, ('.meta', 'source')) or k
            try:
                field = orm_model._meta.get_field(source)
                if field.related_model is None:
                    value = getattr(instance, field.name)
                else:
                    value = self._extract_rel(orm_model, instance, field,
                                              v)
            except FieldDoesNotExist:
                # If instance does not have any field with that name, then
                # check if there is any property-like.
                value = getattr(instance, source)
            data[source] = value
        return data

    def process(self, collection, url, action, context):
        """
        A processor which is responsible for converting a
        `django.db.models.Model` or a `django.db.models.query.QuerySet`
        instance into a python dict.

        This dict holds only the information specified by the spec.
        """
        processor_data = self.read(context)
        instance = processor_data['instance']
        if instance is None:
            self.write(None, context)
            return

        if instance and (not isinstance(instance, Model) and not
                       isinstance(instance, QuerySet)):
            msg = 'A model instance or a queryset is expected. {!r} found.'
            raise InvalidInput(msg.format(type(instance)))
        model = processor_data['model']
        if isinstance(instance, Model):
            instance = None if instance is None else self.to_dict(
                model, instance)
        else:
            instance = [self.to_dict(model, inst) for inst in instance]
        self.write((instance,), context)


def _get_filter_spec(params):
    """
    Extracts field name, operator and value from a query string.
    """
    filter_spec = {}
    for k, v in params.iteritems():
        field_name, _, spec = k.partition('__')
        filter_spec[field_name] = (spec, v)
    return filter_spec


class Filter(object):
    """
    A class to filter a queryset based on a condition.

    Typically, a condition consists of three parts:
        * The field (aka column) based on which filter is executed.
        * Lookup operators, e.g. regex, contains, etc. An absence of a
          lookup operator means exact match.
        * The value which must be satified.

    Args:
        source (string): The name of the field, as it is specified in the
            django models.
    """

    def __init__(self, source=None, **serializer_kwargs):
        self.source = source
        self.serializer_kwargs = serializer_kwargs

    def _get_serializer(self, operator):
        serializer_cls = getattr(self, 'SERIALIZER', None)
        if serializer_cls:
            return serializer_cls(**self.serializer_kwargs)
        return None

    def to_native(self, value, operator):
        """
        Converts value of query parameter into a native represenation, using
        an appropriate serializer.

        If a serializer class is not specified, then the given value is used
        as is.
        """
        serializer = self._get_serializer(operator)
        if serializer:
            return serializer.deserialize(value)
        return value

    def filter(self, operator, queryset, value):
        """
        Filter a given queryset based on a specific lookup operator, and a
        value.
        """
        operators = getattr(self, 'OPERATORS', [])
        if operator and operator not in operators:
            return queryset
        value = self.to_native(value, operator)
        kwargs = {
            self.source + ('__' + operator if operator else ''): value
        }
        return queryset.filter(**kwargs)

    def __call__(self, operator, queryset, value):
        return self.filter(operator, queryset, value)


class BooleanFilter(Filter):
    SERIALIZER = Boolean


class DateFilter(Filter):
    OPERATORS = (
        'gt',
        'gte',
        'lt',
        'lte',
        'range',
    )
    SERIALIZER = Date

    def to_native(self, value, operator):
        """
        Override the conversion of a query parameter to handle the case when
        the 'range' lookup operator is given. This operator expects two dates
        (comma seperated).

        Example:
            /?datefield__range=2015-01-01,2017-01-01
        """
        if operator != 'range':
            return super(DateFilter, self).to_native(value, operator)
        # Then we expect multiple values (comma seperated).
        values = value.split(',')
        if len(values) != 2:
            msg = "Operator 'range' requires two values."
            raise InvalidInput(msg)
        serializer = List(Date(self.serializer_kwargs))
        return serializer.deserialize(values)


class DateTimeFilter(DateFilter):
    SERIALIZER = DateTime


class StringFilter(Filter):
    OPERATORS = (
        'contains',
        'startswith',
        'endswith',
        'regex',
    )


class IntegerFilter(Filter):
    OPERATORS = (
        'gt',
        'gte',
        'lt',
        'lte',
    )
    SERIALIZER = Integer


class FloatFilter(IntegerFilter):
    SERIALIZER = Float


class StructFilter(Filter):
    """
    This class allows nested filtering, i.e. to filter based on the fields
    of a struct entity.
    """
    def __init__(self, filters, source=None, **kwargs):
        super(StructFilter, self).__init__(source=source, **kwargs)
        self.filters = filters

    def filter(self, operator, queryset, value):
        nested_field, _, operator = operator.partition('__')
        filter_obj = self.filters.get(nested_field)
        if not filter_obj:
            return queryset
        filter_obj.source = self.source + '__' + nested_field
        return filter_obj(operator, queryset, value)


def _construct_meta(context):
    node = doc.doc_get(context.top_spec, context.loc[:-1])
    meta = node.get('.meta', {})
    source = meta.get('source', context.parent_name)

    if 'source' in context.spec:
        msg = 'Key {!r} has already been set. ({!s})'
        raise ConflictError(msg.format('source', ','.join(context.loc)))
    return {'source': source}


class Filtering(BaseProcessor):
    """
    A django processor responsible for the filtering of a response, based
    on a query string.
    """
    name = 'apimas.django.processors.Filtering'

    READ_KEYS = {
        'params': 'request/meta/params',
        'queryset': 'response/content',
    }

    WRITE_KEYS = (
        'response/content',
    )

    CONSTRUCTORS = {
        'ref':        Object(Filter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'serial':     Object(Filter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'integer':    Object(IntegerFilter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'float':      Object(FloatFilter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'string':     Object(StringFilter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'text':       Object(StringFilter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'choices':    Object(StringFilter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'email':      Object(StringFilter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'boolean':    Object(BooleanFilter, pre_hook=_construct_meta,
                             conditionals=['.filterable']),
        'datetime':   Object(
                         DateTimeFilter,
                         kwargs_spec_mapping={'format': 'date_format'},
                         kwargs_spec=True, pre_hook=_construct_meta,
                         conditionals=['.filterable']),
        'date':       Object(
                         DateFilter,
                         kwargs_spec_mapping={'format': 'date_format'},
                         kwargs_spec=True, pre_hook=_construct_meta,
                         conditionals=['.filterable']),
        'struct':     Object(
                         StructFilter, args_spec=True,
                         args_spec_name='filters',
                         pre_hook=_construct_meta,
                         conditionals=['.filterable']),
        'default':    Dummy()
    }

    def __init__(self, collection, spec, **meta):
        super(Filtering, self).__init__(collection, spec, **meta)
        field_spec = self.spec.get('*')
        if not field_spec:
            msg = 'Processor {!r}: Node \'*\' of given spec is empty'
            raise InvalidSpec(msg.format(self.name))
        self.spec = field_spec
        self.filters = self._construct()

    def _construct(self):
        instance = doc.doc_construct(
            {}, self.spec, constructors=self.CONSTRUCTORS,
            allow_constructor_input=False, autoconstruct='default',
            construct_spec=True)
        return instance

    def process(self, collection, url, action, context):
        """
        The expected response is a `django.db.models.queryset.QuerySet` object
        returned by a django handler.

        After filtering, this processor substitutes the previous `QuerySet`
        object with the new one.
        """
        processor_data = self.read(context)
        params = processor_data['params']
        queryset = processor_data['queryset']
        if not queryset or not params:
            return
        if not isinstance(queryset, QuerySet):
            msg = 'A queryset is expected, {!r} found'
            raise InvalidInput(msg.format(type(queryset)))
        filter_spec = _get_filter_spec(params)
        for field_name, (operator, value) in filter_spec.iteritems():
            field_spec = self.spec.get(field_name)
            # If a given query parameter is not included in the spec, we just
            # ignore it.
            if not field_spec:
                continue

            filter_obj = self.filters.get(field_name)
            if filter_obj:
                queryset = filter_obj(operator, queryset, value)

        self.write((queryset,), context)


class UserRetrieval(BaseProcessor):
    READ_KEYS = {
        'identity': 'store/auth/identity',
    }

    WRITE_KEYS = (
        'store/auth/user',
    )

    def __init__(self, collection, collection_spec, userid_extractor=None,
                 **meta):
        super(UserRetrieval, self).__init__(
            collection, collection_spec, **meta)
        if userid_extractor:
            userid_extractor = utils.import_object(userid_extractor)
            assert callable(userid_extractor), (
                '"userid_extractor" must be a callable')
        self.userid_extractor = userid_extractor

    def process(self, collection, url, action, context):
        context_data = self.read(context)
        identity = context_data.get('identity')
        if not identity or not self.userid_extractor:
            user_id = None
        else:
            user_id = self.userid_extractor(identity)
        model_backend = ModelBackend()
        user = model_backend.get_user(user_id)
        self.write((user,), context)


class ObjectRetrieval(BaseProcessor):
    READ_KEYS = {
        'model': 'store/orm_model',
        'pk': 'request/meta/pk',
    }

    WRITE_KEYS = (
        'store/instance',
    )

    def process(self, collection, url, action, context):
        context_data = self.read(context)
        model, resource_id = context_data['model'], context_data['pk']
        if model is None:
            loc = self.READ_KEYS['model']
            raise InvalidInput(
                'Processor requires a django model on location {!r},'
                ' nothing found'.format(loc))

        if resource_id is None:
            loc = self.READ_KEYS['pk']
            msg = 'Processor requires a pk on location {!r}, nothing found'
            raise InvalidInput(msg.format(loc))

        instance = django_utils.get_instance(model, resource_id)
        self.write((instance,), context)


def _default_rules():
    return []


def _to_dict(segments, v):
    if len(segments) == 0:
        return v
    return {segments[0]: _to_dict(segments[1:], v)}


def _strip_fields(fields):
    """
    Keep the most generic field definition.

    Example:
    ['foo/bar', 'foo'] => ['foo']
    """
    stripped_fields = {}
    for path in sorted(
            fields,
            cmp=lambda x, y: cmp(len(y.split('/')), len(x.split('/')))):
        stripped_fields.update(_to_dict(path.split('/'), {}))
    return doc.doc_to_ns(stripped_fields).keys()


def _get_allowed_fields(matches, action, data):
    """
    Checks which fields are allowed to be modified or viewed based on
    matches.

    There are two possible scenarios:
        * If request data includes any fields that are not in the list of
          allowed, then an error is raised.
        * Otherwise, it returns the list of allowed fields for later use.
    """
    allowed_keys = {row.field for row in matches}
    data_fields = utils.doc_get_keys(data)
    allowed_keys = set()
    for row in matches:
        if isinstance(row.field, doc.AnyPattern):
            return doc.ANY
        allowed_keys.add(row.field)
    not_allowed_fields = set(data_fields).difference(allowed_keys)
    if not_allowed_fields:
        details = {
            field: 'You do not have permission to write this field'
            for field in not_allowed_fields
        }
        raise AccessDeniedError(details=details)
    return _strip_fields(allowed_keys)


class Permissions(BaseProcessor):
    """
    This processor handles the permissions in a django application.

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

    Specifically, states are matched if calling a class method on the model
    associated with the request returns true. There is a different method for
    checking a state for collection (e.g. list, create, etc) versus resource
    requests. The names and signatures of the methods are as follows:

    Also, this processor saves which fields are allowed to be modified or
    viewed inside request context for later use from other processors.

    >>> class MyModel(models.Model):
    ...     @classmethod
    ...     def check_collection_state_<state name>(cls, row):
    ...         # your code. Return True or False.
    ...
    ...     @classmethod
    ...     def check_resource_state_<state name>(cls, instance, row):
    ...         # your code. Return True or False.
    """
    name = 'apimas.django.processors.Permissions'

    READ_KEYS = {
        'user': 'store/auth/user',
        'model': 'store/orm_model',
        'instance': 'store/instance',
        'content': 'request/content',
    }

    WRITE_KEYS = (
        'store/permissions/allowed_fields',
    )

    _REQUIRED_KEYS = {
        'store/orm_model',
    }

    COLUMNS = ('collection', 'action', 'role', 'field', 'state', 'comment')

    ANONYMOUS_ROLES = ['anonymous']

    _OBJECT_CHECK_PREFIX = 'check_resource_state_'
    _COLLECTION_CHECK_PREFIX = 'check_collection_state_'

    def __init__(self, collection, collection_spec, get_rules=None, **meta):
        super(Permissions, self).__init__(collection, collection_spec, **meta)
        if get_rules is not None:
            self.get_rules = utils.import_object(get_rules)
        else:
            self.get_rules = _default_rules

    def _parse_rules(self, rules):
        """
        Parse given rules and construct the appropriate segment patterns.

        Example:
            '*' => doc.ANY
        """
        parsed_rules = []
        for rule in rules:
            nu_columns = len(self.COLUMNS)
            if len(rule) != nu_columns:
                msg = ('Rules must consist of {!s} columns. An invalid rule'
                       ' found ({!r})')
                raise InvalidInput(msg.format(nu_columns, ','.join(rule)))
            parsed_rules.append([doc.parse_pattern(segment)
                                for segment in rule])
        return parsed_rules

    def _init_rules(self):
        rules = self.get_rules()
        if not rules:
            raise AccessDeniedError(
                'You do not have permisssion to do this action')

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
                'Cannot find propety `apimas_roles` on `user` object')
        return [
                [collection],
                [action],
                roles,
                [doc.ANY],
                [doc.ANY],
                [doc.ANY],
        ]

    def check_state_conditions(self, matches, model, context,
                               instance=None):
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
            prefix = (
                self._OBJECT_CHECK_PREFIX
                if instance is not None
                else self._COLLECTION_CHECK_PREFIX
            )
            method_name = prefix + row.state
            method = getattr(model, method_name, None)
            if callable(method):
                kwargs = {'row': row, 'context': context}
                access_ok = (
                    method(instance, **kwargs)
                    if instance is not None
                    else method(**kwargs)
                )
                state_conditions[row.state] = access_ok
        return state_conditions

    def _get_processor_data(self, context):
        """ Extracts the required keys from request context. """
        context_data = {}
        for stored_key, path in self.READ_KEYS.iteritems():
            value = self.extract(context, path)
            if not value and path in self._REQUIRED_KEYS:
                msg = 'Processor {!r} requires path {!r}, nothing found'
                raise InvalidInput(msg.format(self.name, path))
            context_data[stored_key] = value
        return context_data

    def process(self, collection, action, url, context):
        """
        The steps followed by this processor to determine if there is any
        matching rule are:

        1) Get and parse all permission rules.
        2) Get matches for the first three columns, i.e.
           collection, action, role. If there is not any match, then raise
           an error.
        3) Check which states are valid, and retrieve a subset of matches (
           those matches which meet the valid states). If there is not such
           subset, then raise an error.
        4) Check which fields are allowed to be modified and viewed and modify
           context properly.
        """
        context_data = self._get_processor_data(context)
        rules = self._init_rules()
        pattern_set = self._get_pattern_set(collection, action,
                                            context_data['user'])
        expand_columns = {'field', 'state'}
        matches = list(rules.multimatch(pattern_set, expand=expand_columns))
        if not matches:
            raise AccessDeniedError(
                'You do not have permission to do this action')

        # We check which matching states are valid, and then we get the
        # subset of rules which match the valid states. If the is subset is
        # empty, then the permissions is not granted.
        instance = context_data['instance']
        state_conditions = self.check_state_conditions(
            matches, context_data['model'], context, instance=instance)
        matches = filter((lambda x: state_conditions[x.state]), matches)
        if not matches:
            raise AccessDeniedError(
                'You do not have permission to do this action')

        # As a final step, we save in context the list of fields that allowed
        # to be serialized or deserialized.
        allowed_fields = _get_allowed_fields(
            matches, action, context_data['content'])
        self.write((allowed_fields,), context)

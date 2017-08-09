from copy import deepcopy
from functools import wraps
from apimas import documents as doc
from apimas.errors import InvalidSpec
from apimas.adapters import Adapter


SKIP = object()


def instance_to_node_spec(func):
    """
    A decorator which merges instance and parent spec for backward
    compatibility.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        context = kwargs.get('context')
        context.instance.update(doc.doc_merge(
            context.instance, context.parent_spec, doc.standard_merge))
        return func(*args, **kwargs)
    return wrapper


@instance_to_node_spec
def default_constructor(context):
    return context.instance


class NaiveAdapter(Adapter):
    ADAPTER_CONF = 'adapter_conf'

    TYPE_MAPPING = {
    }

    PROPERTY_MAPPING = {
    }

    EXTRA_PARAMS = {
    }

    SKIP_FIELDS = set()

    def __init__(self):
        self.adapter_spec = None

    def get_constructors(self):
        """
        Get constructor methods for all known predicates.

        By default, a constructor method must be named as
        `construct_<predicate_name>`. If constructor cannot be found, a
        default is provided.
        """
        return {predicate[1:]: getattr(
            self, self.CONSTRUCTOR_PREFIX + '_' + predicate[1:],
            default_constructor) for predicate in self.PREDICATES}

    def construct(self, spec):
        spec = deepcopy(spec)
        self.adapter_spec = doc.doc_construct(
                {}, spec, constructors=self.get_constructors(),
            allow_constructor_input=False, autoconstruct=True,
            construct_spec=True)

    def get_structural_elements(self, instance):
        """
        Get the structural elements from the given instance specification.
        """
        return filter(
            lambda x: not x.startswith('.') and not x == self.ADAPTER_CONF,
            instance.keys()
        )

    @instance_to_node_spec
    def construct_collection(self, context):
        self.init_adapter_conf(context.instance)
        field_schema = doc.doc_get(context.instance, ('*',))
        assert len(context.loc) >= 3
        if not field_schema:
            raise InvalidSpec(
                'A collection must define its field schema.'
                ' Empty collection found: {!r}'.format(
                    context.loc[-2]), loc=context.loc)
        return context.instance

    def construct_type(self, context, field_type=None):
        """
        Contructor for predicates that indicate the type of a field.

        This constructor produces the corresponding spec syntax for
        defining the type of a field according given mapping.
        """
        self.init_adapter_conf(context.instance)
        if field_type not in self.TYPE_MAPPING:
            raise InvalidSpec(
                'Unknown field type: {!r}'.format(field_type), loc=context.loc)
        field_schema = {'type': self.TYPE_MAPPING[field_type]}
        context.instance[self.ADAPTER_CONF].update(field_schema)
        return context.instance

    def validate_structure(self, context):
        if not context.spec:
            raise InvalidSpec(
                'A structure must define its field schema.'
                ' Empty structure found: {!r}'.format(
                    context.loc[-2]), loc=context.loc)
        for k, v in context.spec.iteritems():
            if not isinstance(v, dict):
                msg = ('Not known properties for field {!r} of struct {!r}. A'
                       ' dict with the schema of structure must be provided.')
                raise InvalidSpec(
                    msg.format(k, context.loc[-2]), loc=context.loc)

    @instance_to_node_spec
    def construct_struct(self, context):
        """
        Constructor for `.struct` predicate.

        This maps predicate to the specified type according to mapping.
        """
        self.validate_structure(context)
        return self.construct_type(context, 'struct')

    @instance_to_node_spec
    def construct_structarray(self, context):
        """
        Constructor for `.structarray` predicate.

        This maps predicate to the specified type according to mapping.
        """
        self.validate_structure(context)
        return self.construct_type(context, 'structarray')

    @instance_to_node_spec
    def construct_ref(self, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        Apart from this, it validates that it refers to an existing collection.
        """
        ref = context.spec.get('to', None)
        if not ref:
            raise InvalidSpec(
                'You have to specify `to` parameter', loc=context.loc)
        segments = ref.rsplit('/', 1)
        if len(segments) != 2:
            msg = ('Reference target {!r} cannot be understood'
                   'Must be of the form: <endpoint>/<collection>.')
            raise InvalidSpec(msg.format(ref), loc=context.loc)
        top_spec = context.top_spec
        endpoint, collection = tuple(segments)
        if collection not in top_spec[endpoint]:
            raise InvalidSpec(
                'Reference target {!r} does not exist.'.format(ref),
                loc=context.loc)
        return self.construct_type(context, 'ref')

    @instance_to_node_spec
    def construct_serial(self, context):
        """
        Constuctor for `.serial` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'serial')

    @instance_to_node_spec
    def construct_integer(self, context):
        """
        Constuctor for `.integer` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'integer')

    @instance_to_node_spec
    def construct_biginteger(self, context):
        """
        Constuctor for `.biginteger` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'biginteger')

    @instance_to_node_spec
    def construct_float(self, context):
        """
        Constuctor for `.float` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'float')

    @instance_to_node_spec
    def construct_string(self, context):
        """
        Constuctor for `.string` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'string')

    @instance_to_node_spec
    def construct_text(self, context):
        """
        Constuctor for `.text` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'text')

    @instance_to_node_spec
    def construct_email(self, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'email')

    @instance_to_node_spec
    def construct_boolean(self, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'boolean')

    @instance_to_node_spec
    def construct_datetime(self, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'datetime')

    @instance_to_node_spec
    def construct_date(self, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'date')

    @instance_to_node_spec
    def construct_file(self, context):
        """
        Constuctor for `.file` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(context, 'file')

    @instance_to_node_spec
    def construct_identity(self, context):
        """
        Constructor of `.identity` predicate.

        An `.identity` field is always `readonly`.
        """
        constructors = set(context.cons_siblings + ['.readonly'])
        properties = self.PROPERTIES.intersection(constructors)
        if len(properties) > 1:
            raise InvalidSpec(
                '.identity field {!r} can only be readonly'.format(
                    context.loc[-2]), loc=context.loc)
        if properties != set(['.readonly']):
            msg = '`.identity` field {!r} is always a readonly field.'
            raise InvalidSpec(msg.format(context.loc[-2]), loc=context.loc)
        return context.instance

    @instance_to_node_spec
    def construct_choices(self, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        allowed = context.spec.get('allowed')
        if not isinstance(allowed, (list, tuple)):
            raise InvalidSpec(
                '`choices` property requires a list of allowed values.',
                loc=context.loc)
        return self.construct_type(context, 'choices')

    @instance_to_node_spec
    def construct_blankable(self, context):
        """
        Constuctor for `.blankable` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(context, 'blankable')

    @instance_to_node_spec
    def construct_required(self, context):
        """
        Constuctor for `.required` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(context, 'required')

    @instance_to_node_spec
    def construct_nullable(self, context):
        """
        Constuctor for `.nullable` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(context, 'nullable')

    @instance_to_node_spec
    def construct_readonly(self, context):
        """
        Constuctor for `.readonly` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(context, 'readonly')

    @instance_to_node_spec
    def construct_writeonly(self, context):
        """
        Constuctor for `.readonly` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(context, 'writeonly')

    def construct_property(self, context, property_name):
        """
        Constuctor for predicates that indicate a property of a field,
        e.g. nullable, readonly, required, etc.

        This constructor generates the corresponding spec syntax. However,
        it requires field to be initialized, otherwise, construction is
        defered.
        """
        if property_name not in self.PROPERTY_MAPPING:
            raise InvalidSpec(
                'Unknown property {!r}'.format(property_name),
                loc=context.loc)
        constructed = context.constructed
        predicate_type = self.extract_type(context.instance)
        if predicate_type not in constructed:
            raise doc.DeferConstructor

        if predicate_type in self.SKIP_FIELDS:
            return context.instance
        field_schema = doc.doc_get(context.instance, (self.ADAPTER_CONF,))
        field_schema.update({self.PROPERTY_MAPPING.get(
            property_name, property_name): True})
        return context.instance

    @instance_to_node_spec
    def construct_actions(self, context):
        """
        Constuctor for `.actions` predicate.

        It's a namespace predicate within which we define which REST actions
        are allowed to be performed on the collection.
        """
        return context.instance

    def extract_type(self, instance):
        """
        Method for extracting a predicate whose semantic refers to a type of
        a field from the given instance.
        """
        # Handle case of having `.struct=`, `.structarray=`, etc.
        normalized_keys = [k if not k.endswith('=') else k[:-1]
                           for k in instance.iterkeys()]
        types = set(self.TYPES.intersection(normalized_keys))
        if len(types) > 1:
            msg = 'Type is ambiguous. {!r} found: {!s}'
            raise InvalidSpec(msg.format(len(types), str(types)))
        return None if not types else types.pop()

    def init_adapter_conf(self, instance, initial=None):
        """
        Initialize adapter confication node if it does not already exist.
        """
        if self.ADAPTER_CONF not in instance:
            instance[self.ADAPTER_CONF] = initial if initial is not None\
                else {}
        return instance

    def get_extra_params(self, instance, predicate_type):
        """
        Method to get any extra parameters specified on specification for a
        specific predicate type.

        These parameters contains a default value (in case if they are not
        specified on specification), and a mapping with a key understood by
        adapter.

        :param instance: Current constructed instance of the node.
        :param predicate_type: Type of the constructed node, e.g. .string,
        .integer, etc.

        :returns: A dictionary with extra parameters (as they nderstood by
        adapter).
        """
        params = instance.get(predicate_type, {})
        return {
            v['map']: params.get(k, v['default'])
            for k, v in self.EXTRA_PARAMS.get(
                predicate_type, {}).iteritems()
        }

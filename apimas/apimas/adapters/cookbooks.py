from apimas import documents as doc, exceptions as ex
from apimas.adapters import Adapter


SKIP = object()


def default_constructor(instance, spec, loc, context):
    return instance


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
        self.adapter_spec = doc.doc_construct(
            {}, spec, constructors=self.get_constructors(),
            allow_constructor_input=True, autoconstruct=True)

    def get_structural_elements(self, instance):
        """
        Get the structural elements from the given instance specification.
        """
        filter_func = lambda x: not x.startswith('.')\
            and not x == self.ADAPTER_CONF
        return filter(filter_func, instance.keys())

    def construct_collection(self, instance, spec, loc, context):
        self.init_adapter_conf(instance)
        field_schema = doc.doc_get(instance, ('*',))
        assert len(loc) >= 3
        if not field_schema:
            raise ex.ApimasAdapterException(
                'A collection must define its field schema.'
                ' Empty collection found: {!r}'.format(loc[-2]), loc=loc)
        return instance

    def construct_type(self, instance, spec, loc, context, field_type=None):
        """
        Contructor for predicates that indicate the type of a field.

        This constructor produces the corresponding spec syntax for
        defining the type of a field according given mapping.
        """
        self.init_adapter_conf(instance)
        if field_type not in self.TYPE_MAPPING:
            raise ex.ApimasAdapterException(
                'Unknown field type: {!r}'.format(field_type), loc=loc)
        field_schema = {'type': self.TYPE_MAPPING[field_type]}
        instance[self.ADAPTER_CONF].update(field_schema)
        return instance

    def validate_structure(self, instance, spec, loc, context):
        if not spec:
            raise ex.ApimasAdapterException(
                'A structure must define its field schema.'
                ' Empty structure found: {!r}'.format(loc[-2]), loc=loc)
        for k, v in spec.iteritems():
            if not isinstance(v, dict):
                msg = ('Not known properties for field {!r} of struct {!r}. A'
                       ' dict with the schema of structure must be provided.')
                raise ex.ApimasAdapterException(
                    msg.format(k, loc[-2]), loc=loc)

    def construct_struct(self, instance, spec, loc, context):
        """
        Constructor for `.struct` predicate.

        This maps predicate to the specified type according to mapping.
        """
        self.validate_structure(instance, spec, loc, context)
        return self.construct_type(instance, spec, loc, context, 'struct')

    def construct_structarray(self, instance, spec, loc, context):
        """
        Constructor for `.structarray` predicate.

        This maps predicate to the specified type according to mapping.
        """
        self.validate_structure(instance, spec, loc, context)
        return self.construct_type(
            instance, spec, loc, context, 'structarray')

    def construct_ref(self, instance, spec, loc, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        Apart from this, it validates that it refers to an existing collection.
        """
        ref = spec.get('to', None)
        if not ref:
            raise ex.ApimasAdapterException(
                'You have to specify `to` parameter', loc=loc)
        segments = ref.split('/')
        if len(segments) != 2:
            msg = ('Reference target {!r} cannot be understood'
                   'Must be of the form: <endpoint>/<collection>.')
            raise ex.ApimasAdapterException(msg.format(ref), loc=loc)
        top_spec = context.get('top_spec', {})
        endpoint, collection = tuple(segments)
        if collection not in top_spec[endpoint]:
            raise ex.ApimasAdapterException(
                'Reference targe {!r} does not exist.'.format(ref), loc=loc)
        return self.construct_type(instance, spec, loc, context, 'ref')

    def construct_serial(self, instance, spec, loc, context):
        """
        Constuctor for `.serial` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'serial')

    def construct_integer(self, instance, spec, loc, context):
        """
        Constuctor for `.integer` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'integer')

    def construct_biginteger(self, instance, spec, loc, context):
        """
        Constuctor for `.biginteger` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context,
                                   'biginteger')

    def construct_float(self, instance, spec, loc, context):
        """
        Constuctor for `.float` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context,
                                   'float')

    def construct_string(self, instance, spec, loc, context):
        """
        Constuctor for `.string` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'string')

    def construct_text(self, instance, spec, loc, context):
        """
        Constuctor for `.text` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'text')

    def construct_email(self, instance, spec, loc, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'email')

    def construct_boolean(self, instance, spec, loc, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'boolean')

    def construct_datetime(self, instance, spec, loc, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'datetime')

    def construct_date(self, instance, spec, loc, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'date')

    def construct_file(self, instance, spec, loc, context):
        """
        Constuctor for `.file` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'file')

    def construct_identity(self, instance, spec, loc, context):
        """
        Constructor of `.identity` predicate.

        An `.identity` field is always `readonly`.
        """
        constructors = set(context.get('all_constructors') + ['.readonly'])
        properties = self.PROPERTIES.intersection(constructors)
        if len(properties) > 1:
            raise ex.ApimasAdapterException(
                '.identity field {!r} can only be readonly'.format(loc[-2]),
                loc=loc)
        if properties != set(['.readonly']):
            msg = '`.identity` field {!r} is always a readonly field.'
            raise ex.ApimasAdapterException(msg.format(loc[-2]), loc=loc)
        return instance

    def construct_choices(self, instance, spec, loc, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        allowed = spec.get('allowed')
        if not isinstance(allowed, (list, tuple)):
            raise ex.ApimasAdapterException(
                '`choices` property requires a list of allowed values.',
                loc=loc)
        return self.construct_type(instance, spec, loc, context, 'choices')

    def construct_blankable(self, instance, spec, loc, context):
        """
        Constuctor for `.blankable` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(instance, spec, loc, context,
                                       'blankable')

    def construct_required(self, instance, spec, loc, context):
        """
        Constuctor for `.required` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(instance, spec, loc, context,
                                       'required')

    def construct_nullable(self, instance, spec, loc, context):
        """
        Constuctor for `.nullable` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(instance, spec, loc, context,
                                       'nullable')

    def construct_readonly(self, instance, spec, loc, context):
        """
        Constuctor for `.readonly` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(instance, spec, loc, context,
                                       'readonly')

    def construct_writeonly(self, instance, spec, loc, context):
        """
        Constuctor for `.readonly` predicate.

        This maps predicate to the specified property according to mapping.
        """
        return self.construct_property(instance, spec, loc, context,
                                       'writeonly')

    def construct_property(self, instance, spec, loc, context, property_name):
        """
        Constuctor for predicates that indicate a property of a field,
        e.g. nullable, readonly, required, etc.

        This constructor generates the corresponding spec syntax. However,
        it requires field to be initialized, otherwise, construction is
        defered.
        """
        if property_name not in self.PROPERTY_MAPPING:
            raise ex.ApimasAdapterException(
                'Unknown property {!r}'.format(property_name), loc=loc)
        constructed = context.get('constructed')
        predicate_type = self.extract_type(instance)
        if predicate_type not in constructed:
            raise doc.DeferConstructor

        if predicate_type in self.SKIP_FIELDS:
            return instance
        field_schema = doc.doc_get(instance, (self.ADAPTER_CONF,))
        field_schema.update({self.PROPERTY_MAPPING.get(
            property_name, property_name): True})
        return instance

    def construct_actions(self, instance, spec, loc, context):
        """
        Constuctor for `.actions` predicate.

        It's a namespace predicate within which we define which REST actions
        are allowed to be performed on a collection.
        """
        return instance

    def extract_type(self, instance):
        """
        Method for extracting a predicate whose semantic refers to a type of
        a field from the given instance.
        """
        types = set(self.TYPES.intersection(instance.keys()))
        if len(types) > 1:
            msg = 'Type is ambiguous. {!r} found: {!s}'
            raise ex.ApimasException(msg.format(len(types), str(types)))
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

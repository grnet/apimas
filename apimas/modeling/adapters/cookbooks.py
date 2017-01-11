from apimas.modeling.core import documents as doc, exceptions as ex
from apimas.modeling.adapters import Adapter


SKIP = object()


def default_constructor(instance, spec, loc, context):
    return instance


class NaiveAdapter(Adapter):
    ADAPTER_CONF = 'adapter_conf'

    TYPE_MAPPING = {
    }

    PROPERTY_MAPPING = {
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
            raise ex.ApimasException(
                'A collection must define its field schema.'
                ' Empty collection found: %s' % (loc[-2]))
        return instance

    def construct_type(self, instance, spec, loc, context, field_type=None):
        """
        Contructor for predicates that indicate the type of a field.

        This constructor produces the corresponding spec syntax for
        defining the type of a field according given mapping.
        """
        self.init_adapter_conf(instance)
        if field_type not in self.TYPE_MAPPING:
            raise ex.ApimasException(
                'Unknown field type: `%s`' % (field_type))
        field_schema = {'type': self.TYPE_MAPPING[field_type]}
        instance[self.ADAPTER_CONF].update(field_schema)
        return instance

    def validate_structure(self, instance, spec, loc, context):
        if not spec:
            raise ex.ApimasException(
                'A structure must define its field schema.'
                ' Empty structure found: %s' % (loc[-2]))
        for k, v in spec.iteritems():
            if not isinstance(v, dict):
                raise ex.ApimasException(
                    'Not known properties for field `%s` of struct `%s`' % (
                        k, loc[-2]))

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
            raise ex.ApimasException('You have to specify `to` parameter')
        root_loc = loc[0]
        top_spec = context.get('top_spec', {})
        if ref not in top_spec[root_loc]:
            raise ex.ApimasException(
                'Reference collection `%s` does not exist' % (ref))
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
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'string')

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
            raise ex.ApimasException(
                '.identity field `%s` can only be readonly' % (loc[-2]))
        if properties != set(['.readonly']):
            raise ex.ApimasException(
                '.identity field `%s` is always a readonly field' % (loc[-2]))
        return instance

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
            raise ex.ApimasException(
                'Unknown property name %s' % (property_name))
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

    def extract_type(self, instance):
        """
        Method for extracting a predicate whose semantic refers to a type of
        a field from the given instance.
        """
        types = set(self.TYPES.intersection(instance.keys()))
        if len(types) > 1:
            raise ex.ApimasException('Type is ambiguous. %s found: %s' % (
                len(types), str(types)))
        return None if not types else types.pop()

    def init_adapter_conf(self, instance, initial=None):
        """
        Initialize adapter confication node if it does not already exist.
        """
        if self.ADAPTER_CONF not in instance:
            instance[self.ADAPTER_CONF] = initial if initial is not None\
                else {}
        return instance

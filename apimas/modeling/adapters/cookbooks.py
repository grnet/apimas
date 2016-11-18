from apimas.modeling.core import documents as doc, exceptions as ex
from apimas.modeling.adapters import Adapter


def default_constructor(instance, spec, loc, context):
    return instance


class NaiveAdapter(Adapter):
    ADAPTER_CONF = 'adapter_conf'

    TYPE_MAPPING = {
    }

    PROPERTY_MAPPING = {
    }

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

    def construct_type(self, instance, spec, loc, context, field_type=None):
        """
        Contructor for predicates that indicate the type of a field.

        This constructor produces the corresponding spec syntax for
        defining the type of a field according given mapping.
        """
        self.init_adapter_conf(instance)
        field_schema = {'type': self.TYPE_MAPPING.get(field_type, field_type)}
        instance[self.ADAPTER_CONF].update(field_schema)
        return instance

    def construct_struct(self, instance, spec, loc, context):
        """
        Constructor for `.struct` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'struct')

    def construct_structarray(self, instance, spec, loc, context):
        """
        Constructor for `.structarray` predicate.

        This maps predicate to the specified type according to mapping.
        """
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
        if ref not in doc.doc_get(top_spec, (root_loc,)):
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

    def construct_string(self, instance, spec, loc, context):
        """
        Constuctor for `.ref` predicate.

        This maps predicate to the specified type according to mapping.
        """
        return self.construct_type(instance, spec, loc, context, 'string')

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

    def construct_property(self, instance, spec, loc, context, property_name):
        """
        Constuctor for predicates that indicate a property of a field,
        e.g. nullable, readonly, required, etc.

        This constructor generates the corresponding spec syntax. However,
        it requires field to be initialized, otherwise, construction is
        defered.
        """
        field_schema = doc.doc_get(instance, (self.ADAPTER_CONF,))
        if field_schema is None:
            raise doc.DeferConstructor

        field_schema.update({self.PROPERTY_MAPPING.get(
            property_name, property_name): True})
        return instance

    def extract_type(self, instance):
        """
        Method for extracting a predicate whose semantic refers to a type of
        a field from the given instance.
        """
        types = []
        for predicate in self.TYPES:
            if predicate in instance:
                types.append(predicate)
        if len(types) > 1:
            raise ex.ApimasException('Type is ambiguous. %s found: %s' % (
                len(types), str(types)))
        return None if not types else types[0]

    def init_adapter_conf(self, instance, initial=None):
        """
        Initialize adapter confication node if it does not already exist.
        """
        if self.ADAPTER_CONF not in instance:
            instance[self.ADAPTER_CONF] = initial or {}

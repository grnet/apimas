from collections import Iterable
from django.db import models
from django.core.exceptions import FieldDoesNotExist
from apimas.modeling.core import documents as doc
from apimas.modeling.adapters.cookbooks import NaiveAdapter
from apimas.modeling.adapters.drf.container import Container
from apimas.modeling.adapters.drf.utils import (
    ApimasException, import_object)


def handle_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FieldDoesNotExist as e:
            raise ApimasException(e)
    return wrapper


class DjangoRestAdapter(NaiveAdapter):
    STRUCTURES = {
        '.ref': '.drf_field',
        '.struct': '.drf_field',
        '.structarray': '.drf_field',
        '.collection': '.collection',
    }

    ADAPTER_CONF = 'drf_conf'
    PROPERTIES_CONF_KEY = 'properties'
    NESTED_CONF_KEY = 'nested_objects'

    NON_INTERSECTIONAL_PAIRS = [
        ('read_only', 'write_only'),
        ('required', 'read_only')
    ]

    PROPERTY_MAPPING = {
        'readonly': 'read_only',
        'writeonly': 'write_only',
        'blankable': 'allow_blank',
        'nullable': 'allow_null',
        'required': 'required',
    }

    TYPE_MAPPING = {
        'serial': models.AutoField,
        'integer': models.IntegerField,
        'big-integer': models.BigIntegerField,
        'float': models.FloatField,
        'string': models.CharField,
        'boolean': models.BooleanField,
        'date': models.DateField,
        'datetime': models.DateTimeField,
        'ref': (models.ForeignKey, models.OneToOneField, models.OneToOneRel,
                models.ManyToManyField, models.ManyToOneRel,
                models.ManyToManyRel),
        'structarray': (models.ManyToManyField, models.ManyToOneRel,
                        models.ManyToManyRel),
        'struct': (models.ForeignKey, models.OneToOneField,
                   models.OneToOneRel),
    }

    PREDICATES = list(NaiveAdapter.PREDICATES) + ['.drf_field']

    def __init__(self):
        self.gen_adapter_spec = {}
        self.fields_type = {}
        self.urls = None

    def apply(self):
        """
        Create django rest views based on the constructed adapter spec.
        """
        if not self.adapter_spec:
            raise ApimasException(
                'Cannot apply an empty adapter specification')
        structural_elements = self.get_structural_elements(self.adapter_spec)
        container = Container(structural_elements[0])
        self.urls = container.create_api_views(
            self.adapter_spec.get(self.ADAPTER_CONF, {}))

    def construct_CRUD_action(self, instance, spec, loc, context, action):
        """ Adds an action to the list of allowable. """
        adapter_key = 'allowable_operations'
        self.init_adapter_conf(instance)
        if adapter_key not in instance[self.ADAPTER_CONF]:
            instance[self.ADAPTER_CONF][adapter_key] = []
        instance[self.ADAPTER_CONF][adapter_key].append(action)
        return instance

    def construct_list(self, instance, spec, loc, context):
        """
        Constuctor for `.list` predicate.

        Allows list operation to be performed on a resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'list')

    def construct_retrieve(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows retrieval of specific resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'retrieve')

    def construct_create(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows creation of a new resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'create')

    def construct_update(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows update of a specific resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'update')

    def construct_delete(self, instance, spec, loc, context):
        """
        Constuctor for `.retrieve` predicate.

        Allows deletion of specific resource.
        """
        return self.construct_CRUD_action(instance, spec, loc, context,
                                          'delete')

    def construct_endpoint(self, instance, spec, loc, context):
        """
        Constuctor for `.endpoint` predicate.

        Aggregates all constructed resources in order to form a complete
        API SCHEMA to create all required views.
        """
        adapter_key = 'resources'
        structural_elements = self.get_structural_elements(instance)
        assert len(structural_elements) == 1
        self.init_adapter_conf(instance)
        api_schema = {resource: schema[self.ADAPTER_CONF]
                      for resource, schema in doc.doc_get(
                          instance, (structural_elements[0],)).iteritems()}
        instance[self.ADAPTER_CONF][adapter_key] = api_schema
        return instance

    def construct_collection(self, instance, spec, loc, context):
        """
        Constructor for `.collection` predicate.

        Aggregates constructed field schema and actions in order to form
        schema of a specific resource.
        """
        self.init_adapter_conf(instance)
        resource_schema = self.construct_field_schema(instance)
        resource_schema.update(self.construct_resource_schema(instance))
        instance[self.ADAPTER_CONF].update(dict(
            resource_schema, **spec))
        instance[self.ADAPTER_CONF].update(doc.doc_get(
            instance, ('actions', self.ADAPTER_CONF)) or {})
        return instance

    def construct_drf_field(self, instance, spec, loc, context):
        """
        Constructor of `.drf_field` predicate.

        This constructor validates the existence of a django model field to
        the extracted model class.

        In case of nested fields, e.g. `.struct`, `.structarray`, the field
        should be related to another model.
        """
        nested_fields = {'.struct', '.structarray'}
        if self.ADAPTER_CONF not in instance:
            raise doc.DeferConstructor
        field_type = self.fields_type[loc[-2]]
        context = context.get('top_spec', {})
        self.validate_model_field(context, loc, field_type, **spec)
        for k in nested_fields:
            if k in instance:
                nested = {self.NESTED_CONF_KEY: dict(
                    self.construct_field_schema(instance), **spec)}
                instance[self.ADAPTER_CONF].update(nested)
        return instance

    def construct_type(self, instance, spec, loc, context, field_type=None):
        """
        Contructor for predicates that indicate the type of a field.

        This constructor produces the corresponding cerberus syntax for
        specifying the type of a field.
        """
        self.fields_type[loc[-2]] = self.TYPE_MAPPING[field_type]
        self.init_adapter_conf(instance)
        return instance

    def construct_property(self, instance, spec, loc, context, key):
        """
        Constuctor for predicates that indicate a property of a field,
        e.g. nullable, readonly, required, etc.

        This constructor generates the corresponding cerberus syntax. However,
        it requires field to be initialized, otherwise, construction is
        defered.
        """
        property_path = (self.ADAPTER_CONF, self.PROPERTIES_CONF_KEY)
        field_schema = doc.doc_get(instance, property_path)
        if field_schema is None:
            doc.doc_set(instance, property_path, {})
        self.init_adapter_conf(
            instance, initial={self.PROPERTIES_CONF_KEY: {}})
        instance[self.ADAPTER_CONF][self.PROPERTIES_CONF_KEY].update(
            {self.PROPERTY_MAPPING[key]: True})
        return instance

    @handle_exception
    def validate_model_field(self, spec, loc, django_field_type, source=None):
        """
        Validate that a field specified in spec is field of the model
        given as input.
        """
        django_conf = self.get_constructor_params(spec, loc[:-1], [])
        model = self.extract_model(source or loc[-2], django_conf)
        if model is None:
            raise ApimasException('Invalid argument, model cannot be `None`')
        model_field = model._meta.get_field(source or loc[-2])
        if isinstance(django_field_type, Iterable):
            matches = any(isinstance(model_field, d_field)
                          for d_field in django_field_type)
        else:
            matches = isinstance(model_field, django_field_type)
        if not matches:
            raise ApimasException(
                'Field %s is not %s type in your django model' % (
                    repr(loc[-2]), repr(django_field_type)))

    def validate_intersectional_pairs(self, properties):
        """
        Validate properties of fields.

        There are some properties that cannot be set together, such as
        `required` and `readonly`. This method checks for such violations and
        raises an exception in this case.
        """
        for field_name, prop in properties.iteritems():
            for u, v in self.NON_INTERSECTIONAL_PAIRS:
                if prop.get(u, False) and prop.get(v, False):
                    raise ApimasException(
                        'Field `%s` cannot be both %s and %s' % (
                            field_name, u, v))

    def construct_field_schema(self, instance):
        """ Aggregates propeties of all fields to form a field schema. """
        adapter_key = 'field_schema'
        self.init_adapter_conf(instance)
        field_properties = doc.doc_get(instance, ('*',))
        attrs = {self.PROPERTIES_CONF_KEY: {}, self.NESTED_CONF_KEY: {}}
        for field_name, field_spec in field_properties.iteritems():
            for k, v in attrs.iteritems():
                if k in field_spec[self.ADAPTER_CONF]:
                    v[field_name] = field_spec[self.ADAPTER_CONF][k]
        self.validate_intersectional_pairs(attrs[self.PROPERTIES_CONF_KEY])
        fields = [field_name for field_name, _ in field_properties.iteritems()]
        field_schema = {adapter_key: {
            'fields': fields,
        }}
        for k, v in attrs.iteritems():
            if v:
                field_schema[adapter_key].update({k: v})
        return field_schema

    def get_constructor_params(self, spec, loc, params):
        """
        Get constructor params for all the constructors that represent a
        structure, e.g. `.struct`, `.collection`, etc.
        """
        for structure in self.STRUCTURES.keys():
            struct_doc = doc.doc_get(spec, loc[:-1])
            structure_params = doc.doc_get(
                spec, loc[:-1] + (self.STRUCTURES[structure],))
            if structure in struct_doc and structure_params:
                params.append((structure, structure_params))
        if loc[:-1]:
            return self.get_constructor_params(spec, loc[:-1], params)
        return params

    def extract_model(self, related_field, django_conf):
        """
        Exctact model according to the django configuration.

        However, if a field is related to another model, then the related model
        is extracted.
        """
        _, params = django_conf[0]
        if len(django_conf) > 1:
            return self.extract_related_model(
                params.get('source', related_field), django_conf[1:])
        return import_object(params.get('model', None))

    @handle_exception
    def extract_related_model(self, related_field, django_conf):
        """
        Extracts related model based on given field. It also checks that
        given field is related to another model.
        """
        model = self.extract_model(related_field, django_conf)
        related_field = model._meta.get_field(related_field)
        if related_field.related_model is None:
            raise ApimasException(
                'Field %s is not related with another model' % (
                    repr(related_field)))
        return related_field.related_model

    def construct_resource_schema(self, instance):
        adapter_key = 'filter_fields'
        field_properties = doc.doc_get(instance, ('*',))
        filter_fields = [
            field_name for field_name, spec in field_properties.iteritems()
            if spec.get('.indexable', None) is not None]
        return {adapter_key: filter_fields}

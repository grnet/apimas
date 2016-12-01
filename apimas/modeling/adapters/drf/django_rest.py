from collections import Iterable
from django.db import models
from django.conf.urls import url, include
from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers
from rest_framework import routers
from rest_framework.utils import model_meta
from rest_framework.utils.field_mapping import get_relation_kwargs
from apimas.modeling.core import documents as doc
from apimas.modeling.adapters.drf import utils
from apimas.modeling.adapters.drf.serializers import (
    generate_container_serializer)
from apimas.modeling.adapters.drf.views import generate_view
from apimas.modeling.adapters.cookbooks import NaiveAdapter
from apimas.modeling.adapters.drf.utils import (
    DRFAdapterException, import_object)


def handle_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FieldDoesNotExist as e:
            raise DRFAdapterException(e)
    return wrapper


class DjangoRestAdapter(NaiveAdapter):
    STRUCTURES = {
        '.struct': '.drf_field',
        '.structarray': '.drf_field',
        '.collection': '.drf_collection',
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

    SERILIZERS_TYPE_MAPPING = {
        'serial': serializers.IntegerField,
        'integer': serializers.IntegerField,
        'big-integer': serializers.IntegerField,
        'float': serializers.FloatField,
        'string': serializers.CharField,
        'boolean': serializers.BooleanField,
        'date': serializers.DateField,
        'datetime': serializers.DateTimeField,
        'structarray': serializers.ListSerializer,
        'struct': serializers.Serializer,
        'ref': serializers.HyperlinkedRelatedField,
        'file': serializers.FileField,
    }

    TYPE_MAPPING = {
        'serial': models.AutoField,
        'integer': models.IntegerField,
        'big-integer': models.BigIntegerField,
        'float': models.FloatField,
        'string': (models.CharField, models.TextField),
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
        'file': models.FileField,
    }

    PREDICATES = list(NaiveAdapter.PREDICATES) + [
        '.drf_field', '.drf_collection']

    def __init__(self):
        self.gen_adapter_spec = {}
        self.urls = None

    def apply(self):
        """
        Create django rest views based on the constructed adapter spec.
        """
        if not self.adapter_spec:
            raise DRFAdapterException(
                'Cannot apply an empty adapter specification')
        structural_elements = self.get_structural_elements(self.adapter_spec)
        api = structural_elements[0]
        router = routers.DefaultRouter()
        for collection, spec in doc.doc_get(
                self.adapter_spec, (api,)).iteritems():
            view = spec.get(self.ADAPTER_CONF)
            router.register(collection, view)
        self.urls = url(r'^' + api + '/', include(router.urls))

    def construct_CRUD_action(self, instance, spec, loc, context, action):
        """ Adds an action to the list of allowable. """
        self.init_adapter_conf(instance, initial=[])
        instance[self.ADAPTER_CONF].append(action)
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

    def get_permissions(self, collection, top_spec):
        """
        It constructs permissions rules for every collection.

        Typically, permission rules are provided at a global scope. Then,
        this method, actually matches all permissions rules which are applied
        to a specific collection and then it routes all matches to the
        corresponding path.

        For instance, permission rules applied to collection named
        `mycollection`, they are carried to the path:
        path = (`api`, `mycollection`, `conf`,` permissions`)
        """
        permission_path = ('.endpoint', 'permissions')
        nu_columns = 6
        permission_doc = {}
        permissions = doc.doc_get(top_spec, permission_path) or []
        for rule in permissions:
            doc.doc_set(permission_doc, rule[:-1], rule[-1])
        patterns = [[collection], [doc.ANY], [doc.ANY], [doc.ANY],
                    [doc.ANY]]
        matches = list(doc.doc_match_levels(
            permission_doc, patterns,
            expand_pattern_levels=range(nu_columns)))
        if not matches:
            return None
        return map((lambda x: x[1:]), matches)

    def generate_serializer(self, field_schema, name, model=None,
                            model_serializers=None, extra_serializers=None):
        model_fields, extra_fields, sources = self._classify_fields(
            field_schema)
        serializer = generate_container_serializer(
            model_fields, extra_fields, name, model,
            instance_sources=sources,
            model_serializers=model_serializers,
            extra_serializers=extra_serializers)
        return serializer

    def construct_drf_collection(self, instance, spec, loc, context):
        """
        Constructor for `.drf_collection` predicate.

        Aggregates constructed field schema and actions in order to form
        schema of a specific resource.
        """
        if self.ADAPTER_CONF not in instance:
            raise doc.DeferConstructor
        field_schema = doc.doc_get(instance, ('*',))
        actions = doc.doc_get(instance, ('ations', self.ADAPTER_CONF)) or []
        model = utils.import_object(spec.get('model'))
        model_serializers = spec.pop('model_serializers', [])
        extra_serializers = spec.pop('serializers', [])
        serializer = self.generate_serializer(
            field_schema, loc[-2], model=model,
            model_serializers=model_serializers,
            extra_serializers=extra_serializers)
        kwargs = {k: v for k, v in spec.iteritems() if k != 'model'}
        permissions = self.get_permissions(loc[-2], context.get('top_spec'))
        view = generate_view(loc[-2], serializer, model, actions=actions,
                             permissions=permissions, **kwargs)
        instance[self.ADAPTER_CONF] = view
        return instance

    def _classify_fields(self, field_schema):
        model_fields = {}
        extra_fields = {}
        instance_sources = {}
        for field_name, properties in field_schema.iteritems():
            onmodel = doc.doc_get(properties, ('.drf_field', 'onmodel'))
            field_path = (self.ADAPTER_CONF, 'field')
            instance_path = (self.ADAPTER_CONF, 'source')
            if onmodel:
                model_fields[field_name] = doc.doc_get(properties, field_path)
            else:
                extra_fields[field_name] = doc.doc_get(properties, field_path)
            instance_sources[field_name] = doc.doc_get(properties,
                                                       instance_path)
        return model_fields, extra_fields, instance_sources

    def generate_nested_drf_field(self, instance, loc, predicate_type, model,
                                  **kwargs):
        field_schema = doc.doc_get(instance, (predicate_type,))
        many = predicate_type == 'structarray'
        model_serializers = kwargs.pop('model_serializers', [])
        extra_serializers = kwargs.pop('serializers', [])
        serializer = self.generate_serializer(
            field_schema, loc[-2],
            model_serializers=model_serializers,
            extra_serializers=extra_serializers, model=model)
        return serializer(many=many, **kwargs)

    def get_extra_ref_kwargs(self, name, model):
        model_info = model_meta.get_field_info(model)
        relation_info = model_info.relations[name]
        kwargs = get_relation_kwargs(name, relation_info)
        kwargs.pop('to_field', None)
        return kwargs

    def default_field_constructor(self, instance, spec, loc, context,
                                  predicate_type):
        model = self.validate_model_configuration(
            instance, spec, loc, context, predicate_type)
        path = (self.ADAPTER_CONF,)
        instance_source = spec.pop('instance_source', None)
        field_kwargs = {k: v for k, v in spec.iteritems() if k != 'onmodel'}
        if predicate_type == '.ref':
            field_kwargs.update(self.get_extra_ref_kwargs(loc[-2], model))
        field_kwargs.update(doc.doc_get(instance, path) or {})
        doc.doc_set(instance, (self.ADAPTER_CONF, 'source'), instance_source)
        if predicate_type in self.STRUCTURES:
            drf_field = self.generate_nested_drf_field(
                instance, loc, predicate_type, model, **field_kwargs)
        else:
            drf_field = self.SERILIZERS_TYPE_MAPPING[predicate_type[1:]](
                **field_kwargs)
        doc.doc_set(instance, (self.ADAPTER_CONF, 'field'), drf_field)
        return instance

    def validate_model_configuration(self, instance, spec, loc, context,
                                     predicate_type):
        onmodel = spec.get('onmodel', True)
        source = spec.get('source')
        top_spec = context.get('top_spec')
        model_path = ('.drf_collection', 'model')
        model = utils.import_object(
            doc.doc_get(top_spec, loc[0:2] + model_path))
        if onmodel:
            field_type = self.TYPE_MAPPING[predicate_type[1:]]
            if predicate_type == '.ref':
                _, model, _ = self.validate_ref(
                    instance, spec, loc, top_spec, source)
            else:
                _, model = self.validate_model_field(
                    top_spec, loc, field_type, source)
        return model

    def construct_drf_field(self, instance, spec, loc, context):
        """
        Constructor of `.drf_field` predicate.

        This constructor validates the existence of a django model field to
        the extracted model class.

        In case of nested fields, e.g. `.struct`, `.structarray`, the field
        should be related to another model.
        """
        all_constructors = context.get('all_constructors')
        constructed = context.get('constructed')
        field_constructors = {}
        if len(constructed) < len(all_constructors) - 1:
            raise doc.DeferConstructor
        type_predicate = self.extract_type(instance)
        if type_predicate is None:
            raise utils.DRFAdapterException(
                'Cannot construct drf field `%s` without specifying its'
                ' type' % (loc[-2]))
        return field_constructors.get(
            type_predicate, self.default_field_constructor)(
                instance, spec, loc, context, type_predicate)

    def validate_ref(self, instance, spec, loc, top_spec, source):
        """
        Validates that the referenced field is a foreign key to the same
        django model table as the model defined in the referenced collection
        of spec. Otherwise, an exception with explanatory message is raised.
        """
        root_loc = loc[0:1]
        ref = doc.doc_get(instance, ('.ref', 'to'))
        django_conf = self.get_constructor_params(top_spec, loc, [])
        model = self.extract_model(source or loc[-2], django_conf)
        model_field = model._meta.get_field(source or loc[-2])
        path = root_loc + (ref, '.drf_collection', 'model')
        ref_model = import_object(doc.doc_get(top_spec, path))
        if model_field.related_model is not ref_model:
            raise DRFAdapterException(
                'Model field of %s is not related to %s. Loc: %s' % (
                    source or loc[-2], ref_model, str(loc)))
        return model_field, model, ref_model

    def construct_type(self, instance, spec, loc, context, field_type=None):
        """
        Contructor for predicates that indicate the type of a field.

        This constructor produces the corresponding cerberus syntax for
        specifying the type of a field.
        """
        return instance

    def construct_property(self, instance, spec, loc, context, property_name):
        """
        Constuctor for predicates that indicate a property of a field,
        e.g. nullable, readonly, required, etc.

        This constructor generates the corresponding cerberus syntax. However,
        it requires field to be initialized, otherwise, construction is
        defered.
        """
        self.init_adapter_conf(instance)
        instance[self.ADAPTER_CONF].update(
            {self.PROPERTY_MAPPING[property_name]: True})
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
            raise DRFAdapterException(
                'Invalid argument, model cannot be `None`')
        model_field = model._meta.get_field(source or loc[-2])
        if isinstance(django_field_type, Iterable):
            matches = any(isinstance(model_field, d_field)
                          for d_field in django_field_type)
        else:
            matches = isinstance(model_field, django_field_type)
        if not matches:
            raise DRFAdapterException(
                'Field %s is not %s type in your django model' % (
                    repr(loc[-2]), repr(django_field_type)))
        return model_field, model

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
                    raise DRFAdapterException(
                        'Field `%s` cannot be both %s and %s' % (
                            field_name, u, v))

    def construct_field_schema(self, instance, field_properties, **kwargs):
        """ Aggregates propeties of all fields to form a field schema. """
        adapter_key = 'field_schema'
        self.init_adapter_conf(instance)
        attrs = {self.PROPERTIES_CONF_KEY: {}, self.NESTED_CONF_KEY: {}}
        serializers = kwargs.get('serializers', [])
        for field_name, field_spec in field_properties.iteritems():
            for k, v in attrs.iteritems():
                if k in field_spec[self.ADAPTER_CONF]:
                    v[field_name] = field_spec[self.ADAPTER_CONF][k]
        self.validate_intersectional_pairs(attrs[self.PROPERTIES_CONF_KEY])
        fields = [field_name for field_name, _ in field_properties.iteritems()]
        field_schema = {adapter_key: {
            'fields': fields,
            'serializers': serializers,
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
            struct_doc = doc.doc_get(spec, loc[:-1]) or {}
            structure_params = doc.doc_get(
                struct_doc, (self.STRUCTURES[structure],)) or {}
            onmodel = structure_params.get('onmodel', True)
            if structure in struct_doc and onmodel:
                if structure == '.collection':
                    params.append((structure, structure_params))
                    continue
                source = structure_params.get('source')
                params.append((structure, {'source': source or loc[-2]}))
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
                params.get('source'), django_conf[1:])
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
            raise DRFAdapterException(
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

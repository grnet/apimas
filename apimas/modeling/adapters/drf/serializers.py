import copy
from collections import OrderedDict
from rest_framework import serializers
from rest_framework.settings import api_settings
from rest_framework.utils import model_meta
from apimas.modeling.core.documents import ANY
from apimas.modeling.adapters.drf import utils


NON_INTERSECTIONAL_PAIRS = [
    ('required', 'read_only'),
    ('write_only', 'read_only'),
]


def get_paths(serializer_fields):
    paths = []
    for k, v in serializer_fields.iteritems():
        fields = getattr(v, 'fields', None)
        if fields is None:
            child = getattr(v, 'child', None)
            if child is None:
                nested_paths = []
            else:
                nested_paths = get_paths(child.fields)
        else:
            nested_paths = get_paths(fields)
        paths.extend([k + '/' + p for p in nested_paths] + [k])
    return paths


class ApimasSerializer(serializers.HyperlinkedModelSerializer):
    def __init__(self, *args, **kwargs):
        super(serializers.HyperlinkedModelSerializer, self).__init__(
            *args, **kwargs)
        readonly_fields = self.context['request'].parser_context.get(
            'non_writable_fields', [])
        permitted_fields = self.context['request'].parser_context.get(
            'permitted_fields', [])
        serializer_fields = self.fields
        for field in readonly_fields:
            self.set_field_property(
                field.split('/'), serializer_fields, 'read_only')
        if permitted_fields == ANY:
            return
        non_permitted_fields = set(
            get_paths(serializer_fields)) - set(permitted_fields)
        for field in non_permitted_fields:
            self.set_field_property(field.split('/'), serializer_fields,
                                    'write_only')

    def set_field_property(self, segments, fields, property_key):
        if len(segments) == 1:
            field = fields.get(segments[0])
            if field:
                setattr(field, property_key, True)
            return
        serializer = fields.get(segments[0])
        fields = serializer.child.fields\
            if type(serializer) is serializers.ListSerializer else\
            serializer.fields
        return self.set_field_property(
            segments[1:], fields, property_key)

    def get_fields(self):
        """
        Return the dict of field names -> field instances that should be
        used for `self.fields` when instantiating the serializer.
        """
        if self.url_field_name is None:
            self.url_field_name = api_settings.URL_FIELD_NAME

        assert hasattr(self, 'Meta'), (
            'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        assert hasattr(self.Meta, 'model'), (
            'Class {serializer_class} missing "Meta.model" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        if model_meta.is_abstract_model(self.Meta.model):
            raise ValueError(
                'Cannot use ModelSerializer with Abstract Models.'
            )

        declared_fields = copy.deepcopy(self._declared_fields)
        model = getattr(self.Meta, 'model')
        depth = getattr(self.Meta, 'depth', 0)

        if depth is not None:
            assert depth >= 0, "'depth' may not be negative."
            assert depth <= 10, "'depth' may not be greater than 10."

        # Retrieve metadata about fields & relationships on the model class.
        info = model_meta.get_field_info(model)
        field_names = self.get_field_names(declared_fields, info)

        # Determine any extra field arguments and hidden fields that
        # should be included
        extra_kwargs = self.get_extra_kwargs()
        extra_kwargs, hidden_fields = self.get_uniqueness_extra_kwargs(
            field_names, declared_fields, extra_kwargs
        )

        # Determine the fields that should be included on the serializer.
        fields = OrderedDict()

        for field_name in field_names:
            # If the field is explicitly declared on the class then use that.
            if field_name in declared_fields:
                fields[field_name] = declared_fields[field_name]
                continue

            extra_field_kwargs = extra_kwargs.get(field_name, {})
            source = extra_field_kwargs.get('source') or field_name
            # Determine the serializer field class and keyword arguments.
            field_class, field_kwargs = self.build_field(
                source, info, model, depth
            )

            # Include any kwargs defined in `Meta.extra_kwargs`
            field_kwargs = self.include_extra_kwargs(
                field_kwargs, extra_field_kwargs
            )

            # Create the serializer field.
            fields[field_name] = field_class(**field_kwargs)

        # Add in any hidden fields.
        fields.update(hidden_fields)

        return fields


def generate(model, config, is_collection=True):
    """
    A function to generate a serializer according to the model given
    as parameter.

    Configuration of serializer (which fields will be exposed and how will be
    treated) is defined by the dict given as parameter.

    :param model: The model class required to generate a
    `HyperlinkedModelSerializer` based on it.
    :param config: A dictionary which includes all required configuration of
    serializer.
    :return: A `HyperLinkedModelSerializer` class.
    """
    serializer_class = ApimasSerializer if is_collection\
        else serializers.HyperlinkedModelSerializer
    meta = generate_meta(model, config)
    nested_serializers = generate_nested_serializers(model, config)
    dicts = [meta, nested_serializers]
    # Compose content i.e. nested serializers, Meta class and custom methods.
    class_dict = dict(sum((list(content.items()) for content in dicts), []))
    custom_mixins = map(utils.LOAD_CLASS, config.get(
        utils.SERIALIZERS_LOOKUP_FIELD, []))
    cls = type(model.__name__, tuple(custom_mixins) + (
        serializer_class,), class_dict)
    return cls


CHAR_FIELD = 'CharField'


def get_related_model(model, model_field_name):
    """
    This function get the related model class.

    Based on the given model class and the model field name which corresponds
    to a relation with another model, this function extracts the underlying
    related model class.

    :param model: Model class.
    :param model_field_name: Model field name which corresponds to relation
    with another model.
    :returns: Related model class.

    :raises: DRFAdapterException If the given field is not related to another
    model.
    """

    model_field = model._meta.get_field(model_field_name)
    if model_field.related_model is None:
        raise utils.DRFAdapterException(
            'Field %s is not related with another model' % (
                repr(model_field_name)))
    return model_field.related_model


def get_base_or_proxy(base_model_class, proxy_model_class):
    """
    Get model class to construct model serializer.

    If a proxy model has not been specified, then it gets the base model class.
    If a proxy model has been specified, then it checks that it is actual a
    proxy model of the given base model class.

    :param base_model_class: Base model class of relation.
    :param proxy_model_class: Specified proxy model class.
    :returns: Either the base model class or proxy model class.

    :raises: DRFAdapterException if the given proxy model is not an actual
    proxy model of the defined base model.
    """
    if not proxy_model_class:
        return base_model_class
    if not (proxy_model_class._meta.proxy and
            proxy_model_class._meta.concrete_model is base_model_class):
        raise utils.DRFAdapterException('Given proxy model %s is invalid' % (
            proxy_model_class.__class__.__name__))
    return proxy_model_class


def generate_nested_serializers(model, config):
    """
    This function constructs nested serializers based on the nested relations
    defined on the configuration of parent serializer.

    :param model: Model class which supports nested serialization.
    :param config: Dictionary of serializer configuration.

    :returns: A dictionary keyed by the api field name which corresponds to
    the nested serializer and it maps to the corresponding serializer class.
    """
    nested_objects = config.get(utils.NESTED_OBJECTS_LOOKUP_FIELD, {})
    if not nested_objects:
        return {}
    nested_serializers = {}
    for api_field_name, nested_object in nested_objects.iteritems():
        model_field_name = nested_object.get(utils.MODEL_LOOKUP_FIELD, None)
        rel_model = get_related_model(model, model_field_name)
        serializer_class = generate(rel_model, nested_object.get(
            utils.FIELD_SCHEMA_LOOKUP_FIELD, {}), is_collection=False)
        field = model._meta.get_field(model_field_name)
        many = field.many_to_many or field.one_to_many
        source = None if api_field_name == model_field_name\
            else model_field_name
        extra_kwargs = config.get(utils.EXTRA_KWARGS_LOOKUP_FIELD, {})
        field_kwargs = extra_kwargs.get(api_field_name, {})\
            if extra_kwargs else {}
        nested_serializers[api_field_name] = serializer_class(
            many=many, source=source, **utils.build_field_properties(
                api_field_name, config, field_kwargs))
    return nested_serializers


def generate_meta(model, config):
    """
    Generate `Meta` class of serializer according to the model and the
    configuration object given as parameters.

    :param model: Model class bound to the serializer's `Meta` class.
    :param config: Dictionary which includes all required configuration of
    serializer.
    """
    exposed_fields = config.get(utils.FIELDS_LOOKUP_FIELD, [])
    field_properties = utils.build_properties(exposed_fields, config)
    validate(model, field_properties)
    class_dict = {
        'fields': exposed_fields,
        'extra_kwargs': field_properties,
        'model': model,
    }
    return {'Meta': type('Meta', (object,), class_dict)}


def validate(model, field_properties):
    """
    Validate fields and their properties.

    It is not meaningful for some attributes to be placed together, e.g.
    a field cannot be set as required and read only, etc.
    In addition, only string field can be set as blankable.

    :param model: Model class attached to the generated class of serializer.
    :param field_properties: A dictionary of fields along with their
    properties.
    :raises DRFAdapterException: if there are intersections between lists of
    attributes.
    """
    for field, config in field_properties.iteritems():
        for u, v in NON_INTERSECTIONAL_PAIRS:
            if config.get(u, False) and config.get(v, False):
                raise utils.DRFAdapterException(
                    'Field %s cannot be both %s and %s' % (
                        repr(field), u, v))
        if config.get('allow_blank', False) and (model._meta.get_field(
                field).get_internal_type() != CHAR_FIELD):
            raise utils.DRFAdapterException(
                'Field %s can be set as blankable as it is not CharField' % (
                    repr(field)))

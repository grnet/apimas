from collections import defaultdict
from rest_framework import serializers
from apimas.modeling import utils


NON_INTERSECTION_PAIRS = [
    ('required_fields', 'read_only_fields'),
    ('wrte_only_fields', 'read_only_fields'),
]


PROPERTIES = {
    'read_only_fields': 'read_only',
    'write_only_fields': 'write_only',
    'required_fields': 'required',
    'nullable_fields': 'allow_null',
    'blankable_fields': 'allow_blank',
}


def generate(model, config, is_hyperlinked=True):
    """
    A function to generate a serializer according to the model given
    as parameter.

    Configuration of serializer (which fields will be exposed and how will be
    treated) is defined by the dict given as parameter.

    :param model: The model class required to generate a
    `ModelSerializer` or `HyperlinkedModelSerializer` based on it.
    :param config: A dictionary which includes all required configuration of
    serializer.
    :return: A `ModelSerializer` or `HyperLinkedModelSerializer` class.
    """
    serializer_base_class = serializers.HyperlinkedModelSerializer\
        if is_hyperlinked else serializers.ModelSerializer
    meta = generate_meta(model, config)
    nested_serializers = generate_nested_serializers(model, config)
    dicts = [meta, nested_serializers]
    # Compose content i.e. nested serializers, Meta class and custom methods.
    class_dict = dict(sum((list(content.items()) for content in dicts), []))
    custom_mixins = map(utils.LOAD_CLASS, config.pop('custom_mixins', []))
    cls = type(model.__name__, tuple(custom_mixins) + (
        serializer_base_class,), class_dict)
    return cls


MANY_TO_MANY_REL = 'ManyToManyField'


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

    :raises: ApimasException If the given field is not related to another
    model.
    """
    model_field = model._meta.get_field(model_field_name)
    if model_field.rel is None:
        raise utils.ApimasException(
            'Field %s is not related with another model' % (
                repr(model_field_name)))
    return model_field.rel.to


def get_base_or_proxy(base_model_class, proxy_model_class):
    """
    Get model class to construct model serializer.

    If a proxy model has not been specified, then it gets the base model class.
    If a proxy model has been specified, then it checks that it is actual a
    proxy model of the given base model class.

    :param base_model_class: Base model class of relation.
    :param proxy_model_class: Specified proxy model class.
    :returns: Either the base model class or proxy model class.

    :raises: InvalidProxyModel if the given proxy model is not an actual
    proxy model of the defined base model.
    """
    if not proxy_model_class:
        return base_model_class
    if not (proxy_model_class._meta.proxy and
            proxy_model_class._meta.concrete_model is base_model_class):
        raise utils.ApimasException('Given proxy model %s is invalid' % (
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
    nested_objects = config.get('nested_objects', {})
    if not nested_objects:
        return {}
    nested_serializers = {}
    for api_field_name, nested_object in nested_objects.iteritems():
        model_field_name = nested_object.get('model_field', None)
        rel_model = get_related_model(model, model_field_name)
        serializer_class = generate(rel_model, nested_object.get(
            'field_schema', {}))
        many = model._meta.get_field(
            model_field_name).get_internal_type() == MANY_TO_MANY_REL
        source = None if api_field_name == model_field_name\
            else model_field_name
        extra_kwargs = config.get('extra_kwargs', {})
        field_kwargs = extra_kwargs.get(api_field_name, {})\
            if extra_kwargs else {}
        nested_serializers[api_field_name] = serializer_class(
            many=many, source=source, **build_field_properties(
                [api_field_name], config, field_kwargs).get(
                    api_field_name, {}))
    return nested_serializers


def generate_meta(model, config):
    """
    Generate `Meta` class of serializer according to the model and the
    configuration object given as parameters.

    :param model: Model class bound to the serializer's `Meta` class.
    :param config: Dictionary which includes all required configuration of
    serializer.
    """
    exposed_fields = config.get('fields', [])
    extra_kwargs = config.get('extra_kwargs', {})
    field_properties = build_field_properties(
        exposed_fields, config, extra_kwargs)
    class_dict = {
        'fields': exposed_fields,
        'extra_kwargs': field_properties,
        'model': model,
    }
    return {'Meta': type('Meta', (object,), class_dict)}


def run_constraints(config):
    """
    Run constraints for the field attributes.

    It is not meaningful for some attributes to placed together, e.g.
    a field cannot be set as required and read only, etc.

    :raises ApimasException: if there are intersections between lists of
    attributes.
    """
    for u, v in NON_INTERSECTION_PAIRS:
        inter = set(config.get(u, [])) & set(config.get(v, []))
        if inter:
            raise utils.ApimasException('%s should not both %s and %s' % (
                ','.join(inter), u, v))


def build_field_properties(exposed_fields, config, extra_kwargs):
    """
    This functions builds a dictionary with the exposed fields to API and their
    attributes.

    It actually maps each field to a property according to its specified
    category. For example, fields which are included in the category of
    `required_fields`, they have property `required` as `True`.

    :param exposed_fields: Iterable with the fields exposed to API.
    :param config: Dictionary with the field configuration.

    :returns: A dictionary of exposed fields along with their properties.
    """
    run_constraints(config)
    field_properties = defaultdict(dict, extra_kwargs or {})
    for field in exposed_fields:
        for attr, prop in PROPERTIES.iteritems():
            if field in config.get(attr, []):
                field_properties[field][prop] = True
    return field_properties

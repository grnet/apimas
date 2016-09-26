from rest_framework import viewsets, filters, mixins
from apimas.modeling import utils
from apimas.modeling.serializers import generate as generate_serializer


FILTERING_BACKENDS = {
    'filter_fields': filters.DjangoFilterBackend,
    'search_fields': filters.SearchFilter,
    'ordering_fields': filters.OrderingFilter
}
VIEWSET_ATTRS = [('filter_fields', None), ('ordering_fields', None),
                 ('search_fields', None), ('ordering', None)]


MIXINS = {
    'create': mixins.CreateModelMixin,
    'list': mixins.ListModelMixin,
    'retrieve': mixins.RetrieveModelMixin,
    'update': mixins.UpdateModelMixin,
    'delete': mixins.DestroyModelMixin
}


def generate(model, config, **kwargs):
    """
    A function to generate a viewset according to the model given as
    parameter.

    It constructs a serializer class according to this model and configuration
    of viewset (which methods are allowable, queryset, possible
    filtering/ordering/search fields) is defined on dictionary given as
    parameter.

    :param model: The model class required to generate a
    `ViewSet` based on it.
    :param config: Dictionary with all required configuration of the viewset
    class.
    :return: A `ViewSet` class.
    """
    def get_queryset(self):
        return model.objects.all()

    authentication_classes = config.pop(
        utils.AUTH_CLASSES_LOOKUP_FIELD,
        kwargs.pop(utils.AUTH_CLASSES_LOOKUP_FIELD, []))
    permission_classes = config.pop(
        utils.PERM_CLASSES_LOOKUP_FIELD,
        kwargs.pop(utils.PERM_CLASSES_LOOKUP_FIELD, []))
    field_schema = config.pop(utils.FIELD_SCHEMA_LOOKUP_FIELD, {})
    is_hyperlinked = config.pop(
        utils.HYPERLINKED_LOOKUP_FIELD,
        kwargs.pop(utils.HYPERLINKED_LOOKUP_FIELD, True))
    standard_content = {
        'serializer_class': generate_serializer(
            model, field_schema, is_hyperlinked),
        'get_queryset': get_queryset,
        'authentication_classes': map(
            utils.LOAD_CLASS, authentication_classes),
        'permission_classes': map(utils.LOAD_CLASS, permission_classes)
    }
    attrs = {field: config.get(field, default)
             for field, default in VIEWSET_ATTRS}
    filter_backends = get_filter_backends(config)
    dicts = [standard_content, attrs, filter_backends]
    # Compose content i.e. standard content, attributes, methods.
    class_dict = dict(sum((list(content.items()) for content in dicts), []))
    bases = get_bases_classes(config)
    return type(model.__name__, bases, class_dict)


def get_filter_backends(config):
    """
    Initialize the corresponding Django filter backends if the corresponding
    fields of the viewset class have been assigned.
    """
    filter_backends = ()
    for filter_option, filter_backend in FILTERING_BACKENDS.iteritems():
        value = config.pop(filter_option, None)
        if value:
            filter_backends += (filter_backend,)
    return {'filter_backends': filter_backends}


def get_bases_classes(config):
    """
    This function gets the corresponding base classes in order to construct
    the viewset class.

    A model can specify the allowed operations to it, e.g. update,
    list, delete, etc. Then, a viewset specify the allowed methods based on
    model's allowed operations by defining the corresponding bases classes.

    By default, all methods are allowed.

    Apart from this, also configration object can also include custom mixins
    classes. Therefore, they are also added to the list of bases classes.

    :returns: A tuple of the corresponding base classes.
    """
    bases = ()
    operations = config.pop(utils.OPERATIONS_LOOKUP_FIELD, None)
    bases += (viewsets.ModelViewSet,) if not operations\
        else tuple([MIXINS[operation] for operation in operations]) + (
            viewsets.GenericViewSet,) + tuple(map(utils.LOAD_CLASS, config.pop(
                utils.CUSTOM_MIXINS_LOOKUP_FIELD, [])))
    return bases

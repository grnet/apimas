from rest_framework import filters, viewsets
from apimas.modeling.adapters.drf import (
    utils, mixins, viewsets as apimas_viewsets)
from apimas.modeling.adapters.drf.serializers import (
    generate as generate_serializer)
from apimas.modeling.adapters.drf.permissions import ApimasPermissions


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
    authentication_classes = config.get(
        utils.AUTH_CLASSES_LOOKUP_FIELD,
        kwargs.get(utils.AUTH_CLASSES_LOOKUP_FIELD, []))
    permission_classes = config.get(
        utils.PERM_CLASSES_LOOKUP_FIELD,
        kwargs.get(utils.PERM_CLASSES_LOOKUP_FIELD, []))
    field_schema = config.get(utils.FIELD_SCHEMA_LOOKUP_FIELD, {})
    is_hyperlinked = config.get(
        utils.HYPERLINKED_LOOKUP_FIELD,
        kwargs.get(utils.HYPERLINKED_LOOKUP_FIELD, True))
    permission_classes = map(utils.LOAD_CLASS, permission_classes)
    apimas_perm_cls = gen_apimas_permission_cls(model, config)
    permission_classes += [apimas_perm_cls] if apimas_perm_cls else []
    standard_content = {
        'serializer_class': generate_serializer(
            model, field_schema, is_hyperlinked),
        'queryset': model.objects.all(),
        'authentication_classes': map(
            utils.LOAD_CLASS, authentication_classes),
        'permission_classes': permission_classes
    }
    attrs = {field: config.get(field, default)
             for field, default in VIEWSET_ATTRS}
    filter_backends = get_filter_backends(config)
    dicts = [standard_content, attrs, filter_backends]
    # Compose content i.e. standard content, attributes, methods.
    class_dict = dict(sum((list(content.items()) for content in dicts), []))
    bases = get_bases_classes(config)
    return type(model.__name__, bases, class_dict)


def gen_apimas_permission_cls(model, config):
    """
    Generate an `ApimasPermission` classes that conforms to the permission
    rules specified on the `APIMAS` specfication (if given).
    """
    permissions = config.get('permissions', None)
    if not permissions:
        return None
    return ApimasPermissions(permissions, model)


def get_filter_backends(config):
    """
    Initialize the corresponding Django filter backends if the corresponding
    fields of the viewset class have been assigned.
    """
    filter_backends = ()
    for filter_option, filter_backend in FILTERING_BACKENDS.iteritems():
        value = config.get(filter_option, None)
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
    hook_class = get_hook_class(config)
    custom_mixins = tuple(map(
        utils.LOAD_CLASS, config.get(utils.MIXINS_LOOKUP_FIELD, [])))
    operations = config.get(utils.OPERATIONS_LOOKUP_FIELD, None)
    bases = (apimas_viewsets.ModelViewSet,) if not operations\
        else tuple([MIXINS[operation] for operation in operations]) + (
            viewsets.GenericViewSet,)
    return (hook_class,) + custom_mixins + bases


def get_hook_class(config):
    """
    A simple function for retrieving the hook class to be set to the
    generated ViewSet class.

    If no hook class is specified, then `BaseHook` class is used.
    """
    hook_class = config.get(utils.HOOK_CLASS_LOOKUP_FIELD, None)
    return utils.import_object(hook_class) if hook_class else mixins.HookMixin

from rest_framework import filters, viewsets
from apimas.modeling.adapters.drf import (
    utils, mixins as view_mixins, viewsets as apimas_viewsets)
from apimas.modeling.adapters.drf.permissions import ApimasPermissions


FILTERING_BACKENDS = {
    'filter_fields': filters.DjangoFilterBackend,
    'search_fields': filters.SearchFilter,
    'ordering_fields': filters.OrderingFilter
}
VIEWSET_ATTRS = [('filter_fields', None), ('ordering_fields', None),
                 ('search_fields', None), ('ordering', None)]


MIXINS = {
    'create': view_mixins.CreateModelMixin,
    'list': view_mixins.ListModelMixin,
    'retrieve': view_mixins.RetrieveModelMixin,
    'update': view_mixins.UpdateModelMixin,
    'delete': view_mixins.DestroyModelMixin
}


def generate_view(name, serializer, model, permissions=None,
                  authentication_classes=(), permission_classes=(),
                  mixins=(), hook_class=None, searchable_fields=None,
                  actions=()):
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
    searchable_fields = searchable_fields or {}
    permission_classes = map(utils.LOAD_CLASS, permission_classes)
    apimas_perm_cls = gen_apimas_permission_cls(model, permissions)
    permission_classes += [apimas_perm_cls] if apimas_perm_cls else []
    standard_content = {
        'serializer_class': serializer,
        'queryset': model.objects.all(),
        'authentication_classes': map(
            utils.LOAD_CLASS, authentication_classes),
        'permission_classes': permission_classes
    }
    attrs = {field: searchable_fields.get(field, default)
             for field, default in VIEWSET_ATTRS}
    filter_backends = get_filter_backends(searchable_fields)
    dicts = [standard_content, attrs, filter_backends]
    # Compose content i.e. standard content, attributes, methods.
    class_dict = dict(sum((list(content.items()) for content in dicts), []))
    bases = get_bases_classes(mixins, hook_class, actions)
    return type(name, bases, class_dict)


def gen_apimas_permission_cls(model, permissions):
    """
    Generate an `ApimasPermission` classes that conforms to the permission
    rules specified on the `APIMAS` specfication (if given).
    """
    permissions = permissions or []
    return ApimasPermissions(permissions, model)


def get_filter_backends(searchable_fields):
    """
    Initialize the corresponding Django filter backends if the corresponding
    fields of the viewset class have been assigned.
    """
    filter_backends = ()
    for filter_option, filter_backend in FILTERING_BACKENDS.iteritems():
        value = searchable_fields.get(filter_option, None)
        if value:
            filter_backends += (filter_backend,)
    return {'filter_backends': filter_backends}


def get_bases_classes(mixins, hook_class, actions):
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
    hook_class = hook_class or view_mixins.HookMixin
    bases = (apimas_viewsets.ModelViewSet,) if not actions\
        else tuple([MIXINS[action] for action in actions]) + (
            viewsets.GenericViewSet,)
    return (hook_class,) + mixins + bases


def get_hook_class(config):
    """
    A simple function for retrieving the hook class to be set to the
    generated ViewSet class.

    If no hook class is specified, then `BaseHook` class is used.
    """
    hook_class = config.get(utils.HOOK_CLASS_LOOKUP_FIELD, None)
    return utils.import_object(hook_class) if hook_class\
        else view_mixins.HookMixin

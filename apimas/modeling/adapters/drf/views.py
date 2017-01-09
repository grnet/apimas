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
                  mixins=(), hook_class=None, filter_fields=None,
                  ordering_fields=None, search_fields=None,
                  actions=(), **kwargs):
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
    searchable_fields, filter_backends = get_filtering_options(
        filter_fields, ordering_fields, search_fields)
    dicts = [standard_content, searchable_fields, filter_backends]
    # Compose content i.e. standard content, attributes, methods.
    class_dict = dict(sum((list(content.items()) for content in dicts), []))
    # Update class content with extra attributes.
    class_dict.update(kwargs)
    bases = get_bases_classes(mixins, hook_class, actions)
    return type(name, bases, class_dict)


def get_filtering_options(filter_fields, ordering_fields, search_fields):
    searchable_fields = {
        'filter_fields': filter_fields,
        'ordering_fields': ordering_fields,
        'search_fields': search_fields,
    }
    filter_backends = get_filter_backends(searchable_fields)
    return searchable_fields, filter_backends


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
    hook_class = utils.import_object(hook_class) if hook_class\
        else view_mixins.HookMixin
    mixins = map(utils.LOAD_CLASS, mixins)
    bases = (viewsets.GenericViewSet,) if not actions\
        else tuple([MIXINS[action] for action in actions]) + (
            viewsets.GenericViewSet,)
    return (hook_class,) + tuple(mixins) + tuple(bases)

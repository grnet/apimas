import importlib
from apimas.modeling.core.exceptions import ApimasException


AUTH_CLASSES_LOOKUP_FIELD = 'authentication_classes'
PERM_CLASSES_LOOKUP_FIELD = 'permission_classes'
SER_CLASS_LOOKUP_FIELD = 'serializer_class'
HYPERLINKED_LOOKUP_FIELD = 'hyperlinked'
OPERATIONS_LOOKUP_FIELD = 'allowable_operations'
FIELD_SCHEMA_LOOKUP_FIELD = 'field_schema'
MIXINS_LOOKUP_FIELD = 'mixins'
SERIALIZERS_LOOKUP_FIELD = 'serializers'
NESTED_OBJECTS_LOOKUP_FIELD = 'nested_objects'
FIELDS_LOOKUP_FIELD = 'fields'
MODEL_LOOKUP_FIELD = 'source'
EXTRA_KWARGS_LOOKUP_FIELD = 'properties'
HOOK_CLASS_LOOKUP_FIELD = 'hook_class'

PROPERTIES = {
    'read_only_fields': 'read_only',
    'write_only_fields': 'write_only',
    'required_fields': 'required',
    'nullable_fields': 'allow_null',
    'blankable_fields': 'allow_blank',
}


class DRFAdapterException(ApimasException):
    pass


LOAD_CLASS = lambda x: import_object(x)


def import_object(obj_path):
    if obj_path is None:
        raise DRFAdapterException('Cannot import NoneType object')
    try:
        module_name, obj_name = obj_path.rsplit('.', 1)
        mod = get_package_module(module_name, raise_exception=True)
    except (ValueError, ImportError) as e:
        raise DRFAdapterException(e)
    obj = getattr(mod, obj_name, None)
    if not obj:
        raise DRFAdapterException('Cannot import object %s from %s' % (
            obj_name, module_name))
    return obj


def get_package_module(module_name, raise_exception=False):
    """
    This function loads programtically the desired module which is located in
    the default package. In case, it can't find such a module, it returns
    `None`.

    :param module_name: Name of module inside the package.

    :returns: The module object if it exists; `None` otherwise.
    """
    try:
        return importlib.import_module(module_name)
    except ImportError:
        if raise_exception:
            raise
        return None

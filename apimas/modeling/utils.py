import importlib


class ApimasException(Exception):
    pass


LOAD_CLASS = lambda x: import_object(x)


def import_object(obj_path):
    try:
        module_name, obj_name = obj_path.rsplit('.', 1)
        mod = importlib.import_module(module_name)
    except (ValueError, ImportError) as e:
        raise ApimasException(e)
    obj = getattr(mod, obj_name, None)
    if not obj:
        raise ApimasException('Cannot import object %s from %s' % (
            obj_name, module_name))
    return obj


def get_package_module(module_name):
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
        return None


def get_methods(module):
    """
    This function looks up for specific methods in a specified module and if
    methods exist, then it bounds them to the given class.
    """
    if module is None:
        return {}
    module = get_package_module(module)
    if module is None:
        return {}
    exposed_methods = getattr(module, 'EXPOSED_METHODS', [])
    methods = {}
    for method_name in exposed_methods:
        custom_method = getattr(module, method_name, None)
        if custom_method is not None:
            methods[method_name] = custom_method
    return methods

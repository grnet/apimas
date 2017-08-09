import importlib
from urlparse import urljoin as urlparse_urljoin


def import_object(obj_path):
    if obj_path is None:
        raise ImportError('Cannot import NoneType object')
    module_name, obj_name = obj_path.rsplit('.', 1)
    mod = get_package_module(module_name, raise_exception=True)
    obj = getattr(mod, obj_name, None)
    if not obj:
        raise ImportError('Cannot import object {!r} from {!r}'.format(
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


def get_structural_elements(instance):
    """
    Get the structural elements from the given instance specification.
    """
    return filter(
        lambda x: not x.startswith('.'),
        instance.keys()
    )


def topological_sort(adj):
    """
    Algorithm for topological sorting of a adjacency list, using DFS.

    Args:
        adj (dict): A dictionary of lists representing the adjacency
            list of a graph.

    Returns:
        list: A list of topoloical sorted nodes.

    References:
        [1]: https://en.wikipedia.org/wiki/Topological_sorting
    """
    visited = {k: False for k in adj}
    top_sort = []

    def dfs(adj, k):
        visited[k] = True
        for v in adj.get(k):
            if not visited[v]:
                dfs(adj, v)
        top_sort.append(k)

    for k, v in adj.iteritems():
        if not visited[k]:
            dfs(adj, k)
    return top_sort


def normalize_path(path, sep='/', right_order=False, max_splits=None):
    """
    Converts a string representing a path to a tuple of segments.

    Example: 'foo/bar' -> ('foo', 'bar')
    """
    if isinstance(path, str):
        args = (sep,) if max_splits is None else (sep, max_splits)
        return tuple((
            path.rsplit(*args)
            if right_order
            else path.split(*args)
        ))
    assert isinstance(path, (list, tuple))
    return tuple(path)


def urljoin(*urls):
    """ Constructs a URL based on multiple URL segments. """
    slash = '/'
    url = '/'
    for ufs in urls:
        url = urlparse_urljoin(url, ufs.strip(slash)).strip(slash) + slash
    return url

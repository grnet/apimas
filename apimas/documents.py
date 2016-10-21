from inspect import getargspec
from bisect import bisect_right

class ValidationError(Exception):
    pass


class NotFound(Exception):
    pass


class InvalidInput(Exception):
    pass


class ConflictError(Exception):
    pass


class Context(object):
    pass


def doc_find(doc, path):
    """Walk the given path down the given document.

    The function maintains and finally returns a context of variables:
        feed:     The list of path segments left that have not yet been accessed
        trail:    The list of path segments already accessed
        nodes:    The list of nodes already accessed

    There are two outcomes:
        1. feed is empty, meaning that the given path was found
        2. feed is non-empty, meaning that the first segment in the feed was not
           found in the document at the path formed by trail.

    """
    feed = list(reversed(path))
    trail = []
    nodes = [doc]
    while feed:
        segment = feed.pop()
        if not segment:
            continue

        if not isinstance(doc, dict) or segment not in doc:
            feed.append(segment)
            break

        trail.append(segment)
        doc = doc[segment]
        nodes.append(doc)

    return feed, trail, nodes


def doc_set(doc, path, value):
    if not path:
        m = "Cannot set root document at empty path."
        raise InvalidInput(m)

    feed, trail, nodes = doc_find(doc, path)

    doc = nodes[-1]
    if feed and isinstance(doc, dict):
        # path was not found and parent points to a sub-doc
        doc = nodes[-1]
        for segment in feed[:-1]:
            new_doc = {}
            doc[segment] = new_doc
            doc = new_doc

        doc[feed[-1]] = value
        old_value = None

    else:
        # path was found or stopped in a scalar value, we have to replace the
        # last node
        parent = nodes[-2]
        segment = trail[-1]
        old_value = parent[segment]
        parent[segment] = value

    return old_value


def doc_get(doc, path):
    feed, trail, nodes = doc_find(doc, path)
    return None if feed else nodes[-1]


def doc_iter(doc, preorder=False, postorder=True, path=()):
    if preorder:
        yield path, doc

    for key, val in doc.iteritems():
        subpath = path + (key,)
        if isinstance(val, dict):
            for t in doc_iter(val, preorder=preorder, postorder=postorder,
                              path=subpath):
                yield t
        else:
            yield subpath, val

    if postorder:
        yield path, doc


def doc_pop(doc, path):
    feed, trail, nodes = doc_find(doc, path)
    if feed:
        return

    trail.pop()

    while nodes:
        parent = nodes.pop()
        segment = trail.pop()
        del parent[segment]
        if parent:
            break
    

def doc_merge(doca, docb, merge=lambda a, b: (a, b)):
    docout = {}

    keys = set(doca.keys())
    keys.update(docb.keys())

    for key in keys:
        vala = doca.get(key)
        valb = docb.get(key)

        if isinstance(vala, dict) and isinstance(valb, dict):
            doc = doc_merge(vala, valb, merge=merge)
            if doc:
                docout[key] = doc
        else:
            val = merge(vala, valb)
            if val is not None:
                docout[key] = val

    return docout


_constructors = {}


def register_constructor(constructor, name=None):
    if name is None:
        name = constructor.__name__.replace('construct_', '', 1)

    if name in _constructors:
        m = ("Cannot set constructor {name!r} to {constructor!r}: "
             "constructor already exists.")
        m = m.format(name=name, constructor=constructor)
        raise ConflictError(m)

    argspec = getargspec(constructor)
    req_args = ['instance', 'spec', 'loc']
    if argspec.args != req_args:
        m = "{name!r}: a constructor arguments must be {req_args!r}"
        m = m.format(name=name, req_args=req_args)
        raise InvalidInput(m)

    _constructors[name] = constructor


def unregister_constructor(name):
    return _constructors.pop(name, None)


def autoconstructor(instance, spec, loc):
    if type(instance) is dict:
        instance[loc[-1]] = spec

    return instance


register_constructor(autoconstructor, name='.autoconstruct')


def doc_construct(doc, spec, loc=(),
                  constructors=_constructors,
                  autoconstruct=False,
                  allow_constructor_input=False):

    instance = {}
    constructor_names = []
    doc_is_basic = type(doc) is not dict
    constructed_data_keys = set()
    if type(spec) is not dict:
        m = "{loc!r}: 'spec' must be a dict, not {spec!r}"
        m = m.format(loc=loc, spec=spec)
        raise InvalidInput(m)

    prefixes = []

    for key in spec.iterkeys():
        if doc_is_basic:
            subloc = loc + (key,)
            m = ("{loc!r}: document {doc!r} is basic "
                 "but spec requires key {key!r}")
            m = m.format(loc=subloc, doc=doc, key=key)
            raise ValidationError(m)

        if key.endswith('*'):
            prefixes.append(key[:-1])

        if key.startswith('.'):
            constructor_names.append(key)
            if not allow_constructor_input:
                continue

        subspec = spec[key]
        subdoc = doc[key] if key in doc else {}
        subloc = loc + (key,)
        instance[key] = doc_construct(
            doc=subdoc, spec=subspec, loc=subloc,
            constructors=constructors,
            autoconstruct=autoconstruct,
            allow_constructor_input=allow_constructor_input)
        constructed_data_keys.add(key)

    prefixes.sort()

    if not doc_is_basic:
        for key in doc:
            if key in constructed_data_keys:
                continue

            index = bisect_right(prefixes, key) - 1
            subspec = {}
            if index >= 0:
                prefix = prefixes[index]
                if key.startswith(prefix):
                    subspec = spec[prefix + '*']

            subloc = loc + (key,)
            subdoc = doc[key]
            instance[key] = doc_construct(
                doc=subdoc, spec=subspec, loc=subloc,
                constructors=constructors,
                autoconstruct=autoconstruct,
                allow_constructor_input=allow_constructor_input)

    for constructor_name in constructor_names:
        subloc = loc + (key,)
        if constructor_name in constructors:
            constructor = constructors[constructor_name]
        elif autoconstruct in constructors:
            constructor = constructors[autoconstruct]
        else:
            m = "{loc!r}: cannot find constructor {constructor_name!r}"
            m = m.format(loc=subloc, constructor_name=constructor_name)
            raise InvalidInput(m)

        instance = constructor(instance=instance, spec=spec[constructor_name],
                               loc=subloc)

    return instance


def doc_inherit(doc, path, inherit_path):
    feed, trail, nodes = doc_find(doc, path)
    if feed:
        return None

    inh_nodes = [nodes[0]]
    inh_paths = []
    for i in xrange(len(trail)):
        inh_paths.append(trail[:i])
        inh_nodes.append(nodes[i + 1])

    return inh_paths, inh_nodes


def doc_search(doc, name):
    findings = []
    for path, doc in doc_iter(doc):
        if path and path[-1] == name:
            findings.append(path)
    return findings


def doc_from_ns(ns, sep='/'):
    docout = {}
    for key, value in ns.iteritems():
        path = key.strip('/').split('/')
        doc_set(docout, path, value)


def doc_to_ns(doc, sep='/'):
    ns = {}
    for path, val in doc_iter(doc):
        ns[sep.join(path)] = val
    return ns


def random_doc(nr_nodes=32, max_depth=7):
    words = (
        'alpha',
        'beta',
        'gamma',
        'delta',
        'epsilon',
        'zeta',
        'eta',
        'theta',
        'iota',
        'kappa',
        'lambda',
        'mu',
        'nu',
        'omikron',
        'pi',
        'rho',
        'sigma',
        'tau',
        'ypsilon',
        'phi',
        'psi',
        'omega',
        'zero',
        'one',
        'two',
        'three',
        'four',
        'five',
        'six',
        'seven',
        'eight',
        'nine',
    )

    import random

    doc = {}

    for i in xrange(nr_nodes):
        depth = random.randint(1, max_depth)
        path = tuple(random.choice(words) for _ in xrange(depth))
        doc_set(doc, path, random.choice(words))

    return doc


def test():
    from pprint import pprint
    doc = random_doc()
    pprint(doc)


if __name__ == '__main__':
    test()

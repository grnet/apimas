"""Docular.

A generic recursive object-document manipulation, specification,
and construction toolkit.

"""
import re
from itertools import izip_longest

bytes = str


def doc_locate(doc, path):
    """Walk a path down a document.

    The path is a list of bytestring segments.
    Starting from the root node, a cursor points at the first segment.

    At each node, the segment under the cursor is used
    to access the node to go deeper.

    As the cursor moves from the begining towards the end of the segment list,
    the list is logically split into two parts.

    The first part, the trail, is the prefix of segments
    that have already been used in descending through the document hierarchy
    and corresponds to the current path.

    The second part of the path, the feed, is the suffix of segments
    that have not yet been accessed to descend to the full path.

    There are two outcomes:
        1. feed is empty, meaning that the given path was found
        2. feed is non-empty, meaning that the first segment in the feed was
           not found in the document at the path formed by the trail.

    Args:
        doc (dict):
            A recursive object-document
        path (tuple):
            A sequence of path segments as in ('path', 'to', 'somewhere')

    Returns:
        tuple of lists:
            feed (list):
                List of path segments left that have not yet been accessed
            trail (list):
                List of path segments already accessed. It corresponds to the
                current path of the node where no further descent was possible
                and thus doc_locate() was terminated.
            nodes (list):
                List of nodes already accessed, in order.
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


def doc_set(doc, path, value, multival=False):
    if not path:
        return value

    feed, trail, nodes = doc_locate(doc, path)

    doc = nodes[-1]
    if feed and isinstance(doc, dict):
        # path was not found and parent points to a sub-doc
        doc = nodes[-1]
        while True:
            segment = feed.pop()
            if not feed:
                break
            new_doc = {}
            doc[segment] = new_doc
            doc = new_doc

        doc[segment] = value
        old_value = None

    else:
        # path was found or stopped in a scalar value, we have to replace the
        # last node with a hierarchy from feed
        parent = nodes[-2]
        segment = trail[-1]
        old_value = parent[segment]
        new_value = value
        for key in feed:
            new_value = {key: new_value}
        if not multival:
            parent[segment] = new_value
        elif hasattr(old_value, 'append'):
            old_value.append(new_value)
        else:
            parent[segment] = [old_value, new_value]

    return old_value


def doc_get(doc, path):
    feed, trail, nodes = doc_locate(doc, path)
    return None if feed else nodes[-1]


class elem(long):

    __slots__ = ()

    def __repr__(self):
        return 'elem({0})'.format(long.__repr__(self)[:-1])

    str = __repr__


def doc_iter(doc, preorder=None, postorder=None, path=(),
             ordered=False, multival=False):

    """Iterate the document hierarchy yielding each path and node.

    Args:

        doc (dict):
            A hierarchical object-document

        preorder (bool):
            If true, yield path and node at the first node visit.

        postorder (bool):
            If true, yield path and node at the second node visit.

            Note that postorder is independent from preorder.
            If both are true, nodes will be yielded two times.
            If none is true, doc is iterated for any possible side-effects,
            but nothing is yielded.

            If no preorder or postorder is given,
            then postorder defaults to True and preorder to False.
            Otherwise, if preorder or postorder is false,
            then the other defaults to True.

        path (tuple):
            A prefix path to append in yielded paths

        ordered (bool):
            If keys within a node will be visited in a sorted order or not.

        multival:
            When true, lists, tuples, and sets are entered as subdocuments.
            Their elements are enumerated and their index is appended in the
            path as elem(long)

    Yields:

        tuple of (path, node):
            path (tuple):
                The segments of the current path
            node (dict):
                The node at the current path.

    Receives:

        None or True:
            If None is received, iteration continues normally.
            If True is received, iteration skips current node.
            Note that skip only works if preorder=True, otherwise
            there will be no chance to send True before the nod
            children are visited.
    """
    skip = None

    if preorder is None:
        if postorder is None:
            postorder = True
        elif not postorder:
            preorder = True
    elif not preorder and postorder is None:
        postorder = True

    if preorder:
        skip = (yield path, doc)

    if not skip:
        doc_type = type(doc)
        if multival and doc_type in (list, tuple, set):
            for i, val in enumerate(doc):
                subpath = path + (elem(i),)
                g = doc_iter(val,
                             preorder=preorder, postorder=postorder,
                             path=subpath, multival=multival)
                try:
                    skip = None
                    while True:
                        skip = yield g.send(skip)
                except StopIteration:
                    pass

        elif doc_type is dict:
            iteritems = sorted(doc.iteritems()) if ordered else doc.iteritems()
            for key, val in iteritems:
                subpath = path + (key,)
                g = doc_iter(val,
                             preorder=preorder, postorder=postorder,
                             path=subpath, multival=multival)
                try:
                    skip = None
                    while True:
                        skip = yield g.send(skip)
                except StopIteration:
                    pass

    if postorder:
        yield path, doc


def doc_pop(doc, path):

    """Remove and return the node that exists at the given path.

    Args:

        doc (dict):
            a hierarchical object-document.

        path (tuple):
            a list of str segments forming a path in doc.

    Returns:

        None or dict:
            If there exists a node at the given path, it is removed and
            returned. Any resulting empty nodes are removed. If there is no
            node at the path, None is returned.

    """
    feed, trail, nodes = doc_locate(doc, path)
    if feed:
        return None

    popped_node = nodes.pop()

    while nodes:
        segment = trail.pop()
        parent = nodes.pop()
        del parent[segment]
        if parent:
            break

    return popped_node


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


def doc_update(target, source, multival=False):
    for path, val in doc_iter(source):
        if type(val) is not dict:
            doc_set(target, path, val, multival=multival)
    return target


def doc_inherit_all(doc, path, key):
    feed, trail, nodes = doc_locate(doc, path)
    inheritance = []
    loc = []
    for segment, node in izip_longest(trail, nodes):
        if key in node:
            inheritance.append((tuple(loc), node[key]))
        loc.append(segment)
    return inheritance


def doc_inherit(doc, path, key, default=None):
    feed, trail, nodes = doc_locate(doc, path)
    for node in reversed(nodes):
        if key in node:
            return node[key]
    return default


def doc_inherit2(doc, path, keyloc, default=None):
    feed, trail, nodes = doc_locate(doc, path)
    for node in reversed(nodes):
        value = doc_get(node, keyloc)
        if value is not None:
            return value
    return default


def doc_search_name(doc, name):
    findings = []
    for path, doc in doc_iter(doc):
        if path and path[-1] == name:
            findings.append(path)
    return findings


def doc_search_regex(doc, regex):
    matcher = re.compile(regex)
    findings = []
    for path, doc in doc_iter(doc):
        if path and matcher.match(path[-1]):
            findings.append(path)
    return findings


def doc_from_ns(ns, sep='/'):
    docout = {}
    for key, value in ns.iteritems():
        path = key.strip(sep).split(sep)
        doc_set(docout, path, value)
    return docout


def doc_iter_leaves(doc):
    for path, val in doc_iter(doc):
        if not val or type(val) is not dict:
            yield path, val


def doc_to_ns(doc, sep='/'):
    ns = {}
    for path, val in doc_iter_leaves(doc):
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

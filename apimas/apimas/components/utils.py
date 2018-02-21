class Singleton(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<%s>' % self.name


def collect_paths(doc, prefix=()):
    paths = set()

    if isinstance(doc, list):
        for elem in doc:
            paths.update(collect_paths(elem, prefix))
        return paths

    if isinstance(doc, dict):
        for subkey, subdoc in doc.iteritems():
            prefixed_key = prefix + (subkey,)
            paths.update(collect_paths(subdoc, prefixed_key))
        return paths

    if prefix:
        paths.add(prefix)

    return paths

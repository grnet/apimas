class Singleton(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<%s>' % self.name


def expand_doc_keys(doc, prefix=()):
    paths = set()
    if prefix:
        paths.add(prefix)

    if not isinstance(doc, dict):
        return paths

    for subkey, subdoc in doc.iteritems():
        prefixed_key = prefix + (subkey,)
        paths.update(expand_doc_keys(subdoc, prefixed_key))
    return paths

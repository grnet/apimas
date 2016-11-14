from apimas.modeling.core import documents as doc

prefix = doc.Prefix('abc')

patterns = {
    ('a', 'c', 'd'): {},
    ('a', 'c', 'b'): {},
    ('a', 'k', 'a'): {},
    (prefix, 'c', doc.Prefix('k')): {},
    (prefix, 'c', 'fda'): {},
}


rules = {
    ('a', 'c', 'a'): {},
    ('a', 'c', 'b'): {},
    ('a', 'k', 'a'): {},
    ('abcka', 'c', 'k'): {},
    ('abckal', 'c', 'kal'): {},
    ('abckal', 'c', 'kelo'): {},
}


callables = [
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
]


def convert(ns):
    docout = {}
    for key, value in ns.iteritems():
        doc.doc_set(docout, key, value)
    return docout


rules_doc = convert(rules)
patterns_doc = convert(patterns)
docs, aggreement = doc.doc_match(
    patterns_doc, rules_doc, callables, expand_levels=[], automerge=True)
print docs, aggreement

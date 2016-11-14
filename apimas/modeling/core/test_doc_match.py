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
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
    doc.AnyOfAggregator(),
]


def ns_to_doc_patterns(ns):
    docout = {}
    for key, value in ns.iteritems():
        doc.doc_set(docout, key, value)
    return docout


def test_random():
    for i in xrange(1000):
        random_doc = doc.random_doc()
        pattern_sets = []
        for p, v in doc.doc_iter(random_doc):
            max_level = len(p)
            nr_sets = len(pattern_sets)
            level_diff = max_level - nr_sets + 1
            if max_level >= nr_sets:
                pattern_sets += [set() for _ in xrange(level_diff)]
            for level, segment in enumerate(p):
                pattern_sets[level].add(p[level])

        matched = doc.doc_match_levels(random_doc, pattern_sets,
                                       expand_pattern_levels=())
        matched_doc = {}
        for p in matched:
            doc.doc_set(matched_doc, p[:-1], p[-1])

        assert random_doc == matched_doc

        matched = doc.doc_match(random_doc, random_doc, callables,
                                expand_levels=(), automerge=True)

        assert random_doc == matched_doc


def test_basic():
    from pprint import pprint
    rules_doc = ns_to_doc_patterns(rules)
    patterns_doc = ns_to_doc_patterns(patterns)
    docs, aggreement = doc.doc_match(
        patterns_doc, rules_doc, callables, expand_levels=[0, 2])
    pprint(docs)
    pprint(aggreement)

    pattern_sets = doc.doc_to_level_patterns(patterns_doc)[:-1]
    mm = list(doc.doc_match_levels(rules_doc, pattern_sets,
                                   expand_pattern_levels=[0, 2]))
    pprint(mm)


if __name__ == '__main__':
    test_basic()
    test_random()
    #import cProfile
    #cProfile.run('test_random()')

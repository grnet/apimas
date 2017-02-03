from documents import (
    random_doc, doc_pop, doc_match_levels, doc_iter, doc_construct,
    doc_set, doc_get, Prefix)


def test():
    from pprint import pprint
    doc = random_doc()
    pprint(doc)
    a = {'hello': {'there': 9}, 'hella': {'off': 11, 'true': 12}}
    print doc_pop(a, 'hello.there'.split('.'))
    pprint(a)
    print doc_pop(a, 'hella'.split('.'))
    pprint(a)

    def constructor(instance, spec, loc, context):
        assert '.one' in instance
        assert '.three' in instance
        assert context['parent_name'] == (loc[1:2] and loc[-2])
        assert context['parent_spec'] == doc_get(context['top_spec'], loc[:-1])
        return instance

    spec = {'.one': 'two', '.three': 'four'}
    instance = doc_construct({}, spec,
                             allow_constructor_input=True,
                             constructors = {'one': constructor,
                                             'three': constructor,},
                             autoconstruct=True)

    rules_doc = {
        'one': {
            'two': 2,
            'three': 3,
        },
        'four': 4,
        '.patterns': {
            '_foo': 'baz',
        },
        'five': {
            'six': 6,
            'seven': {
                'eight': 8,
                '.patterns': {
                    '_nine_': 9,
                },
            },
        },
    }

    rules_doc = doc_construct({}, rules_doc, autoconstruct=True)

    pattern_sets = [
        {'one', 'four', Prefix('f')},
        {'two', 'three', Prefix('s')},
        {'looloo', 'nine_tails', 'nine_eights', 'eight'},
        {'nothing', 'noonoo'},
    ]

    pprint(rules_doc)
    pprint(pattern_sets)

    for expand_pattern_levels in [{}, {0,1,2,3}]:
        print "EXPAND", expand_pattern_levels

        matches = list(doc_match_levels(rules_doc, pattern_sets,
                                        expand_pattern_levels))
        pprint(matches)
        match_doc = {}
        for match in matches:
            doc_set(match_doc, match[:-1], match[-1], multival=True)

        print "MULTIVAL"
        pprint([p for p, v in doc_iter(match_doc, ordered=True, multival=True)])


    skippable = {
        'a': {
            '1': {
                'hello': 'there',
                'my': 'friend',
            },
            '2': {
                'how': 'are',
                'you': 'doing',
            },
        },
        'b': {
            '3': {
                'this': 'fine',
                'day': 'today',
            },
            '4': {
                'I': 'myself',
                'am': 'good',
            },
        },
    }

    g = doc_iter(skippable, ordered=True, preorder=True, postorder=False)
    try:
        skip = None
        while True:
            path, val = g.send(skip)
            print path, '=', val
            skip = True if path == ('a', '2') else False
    except StopIteration:
        pass


if __name__ == '__main__':
    test()

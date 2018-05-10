from docular import (
    doc_locate,
    doc_set,
    doc_get,
    doc_iter,
    doc_pop,
    doc_merge,
    doc_update,
    doc_inherit_all,
    doc_inherit,
    doc_inherit2,
    doc_search_name,
    doc_search_regex,
    doc_from_ns,
    doc_to_ns,
    random_doc,
    doc_spec_get,
    doc_spec_set,
    doc_spec_iter,
    doc_spec_merge,
    make_constructor,
    doc_compile_spec,
    doc_strip_spec,
    doc_spec_register_predicate,
    doc_spec_register_constructor,
    doc_spec_config,
    doc_spec_construct,
    doc_construct,
    construct_after,
    construct_last,
    report_errors,
)


from docular import (
    Error,
    InvalidInput,
    MergeFault,
)


from copy import deepcopy


doc = {
    'a': {
        'b': {
            'c': {
                'd': 9,
            },
        },
    },
    'b': {
        'c': -1,
    },
}


def test_doc_locate():
    path = ('x', 'y', 'z')
    feed, tail, nodes = doc_locate(doc, path)

    assert feed == list(reversed(path))
    assert tail == []
    assert nodes == [doc]

    path = ('a', 'b', 'c')
    feed, tail, nodes = doc_locate(doc, path)

    assert feed == []
    assert tail == ['a', 'b', 'c']
    assert nodes == [doc, doc['a'], doc['a']['b'], doc['a']['b']['c']]

    path = ('a', 'b', 'w', 'z')
    feed, tail, nodes = doc_locate(doc, path)

    assert feed == ['z', 'w']
    assert tail == ['a', 'b']
    assert nodes == [doc, doc['a'], doc['a']['b']]


def test_doc_set():
    new_doc = deepcopy(doc)
    doc_set(new_doc, ('a', 'b', 'c', 'd'), -9, multival=True)
    assert new_doc['a']['b']['c']['d'] == [9, -9]

    doc_set(new_doc, ('a', 'b', 'c', 'd'), -99, multival=True)
    assert new_doc['a']['b']['c']['d'] == [9, -9, -99]

    doc_set(new_doc, ('a', 'b', 'c', 'd'), -9)
    assert new_doc['a']['b']['c']['d'] == -9

    doc_set(new_doc, ('a', 'b', 'c', 'd'), 9)
    assert new_doc == doc

    doc_set(new_doc, ('b', 'g'), 3)
    assert new_doc['b'] == {'c': -1, 'g': 3}

    doc_set(new_doc, ('b', 'c', 'd', 'e'), 5)
    assert new_doc['b']['c'] == {'d': {'e': 5}}

    del new_doc['b']['g']
    doc_set(new_doc, ('b', 'c'), -1)
    assert new_doc == doc


def test_doc_get():
    val = doc_get(doc, ())
    assert val == doc

    val = doc_get(doc, ('a', 'b', 'c'))
    assert val == doc['a']['b']['c']

    val = doc_get(doc, ('a', 'b', 'z'))
    assert val is None


def test_doc_iter():

    postorder_path_and_nodes = [
        (('a', 'b', 'c', 'd'), 9),
        (('a', 'b', 'c'), {'d': 9}),
        (('a', 'b'), {'c': {'d': 9}}),
        (('a',), {'b': {'c': {'d': 9}}}),
        (('b', 'c'), -1),
        (('b',), {'c': -1}),
        ((), {'a': {'b': {'c': {'d': 9}}}, 'b': {'c': -1}}),
    ]

    path_and_nodes = list(doc_iter(doc, ordered=True))
    assert path_and_nodes == postorder_path_and_nodes

    path_and_nodes = list(doc_iter(doc, ordered=True, postorder=True))
    assert path_and_nodes == postorder_path_and_nodes

    preorder_path_and_nodes = [
        ((), {'a': {'b': {'c': {'d': 9}}}, 'b': {'c': -1}}),
        (('a',), {'b': {'c': {'d': 9}}}),
        (('a', 'b'), {'c': {'d': 9}}),
        (('a', 'b', 'c'), {'d': 9}),
        (('a', 'b', 'c', 'd'), 9),
        (('b',), {'c': -1}),
        (('b', 'c'), -1),
    ]

    path_and_nodes = list(doc_iter(doc, ordered=True, preorder=True))
    assert path_and_nodes == preorder_path_and_nodes

    path_and_nodes = list(doc_iter(doc, ordered=True,
                                   preorder=True, postorder=False))
    assert path_and_nodes == preorder_path_and_nodes

    prepostorder_path_and_nodes = [
        ((), {'a': {'b': {'c': {'d': 9}}}, 'b': {'c': -1}}),
        (('a',), {'b': {'c': {'d': 9}}}),
        (('a', 'b'), {'c': {'d': 9}}),
        (('a', 'b', 'c'), {'d': 9}),
        (('a', 'b', 'c', 'd'), 9),
        (('a', 'b', 'c', 'd'), 9),
        (('a', 'b', 'c'), {'d': 9}),
        (('a', 'b'), {'c': {'d': 9}}),
        (('a',), {'b': {'c': {'d': 9}}}),
        (('b',), {'c': -1}),
        (('b', 'c'), -1),
        (('b', 'c'), -1),
        (('b',), {'c': -1}),
        ((), {'a': {'b': {'c': {'d': 9}}}, 'b': {'c': -1}}),
    ]

    path_and_nodes = list(doc_iter(doc, ordered=True,
                                   preorder=True, postorder=True))
    assert path_and_nodes == prepostorder_path_and_nodes

    path_and_nodes = list(doc_iter(doc, ordered=True,
                                   preorder=False, postorder=False))
    assert path_and_nodes == []


def test_doc_pop():
    new_doc = deepcopy(doc)
    val = doc_pop(new_doc, ('a', 'b', 'c'))
    assert val == {'d': 9}
    assert new_doc == {'b': {'c': -1}}


def test_doc_merge():
    other_doc = {
        'a': {'b': {'c': {'d': -9}}},
        'c': {'d': 0},
        'b': {'c': {'d': 1}},
    }

    def merge(x, y):
        if x is None:
            return y
        if y is None:
            return x
        return (x, y)

    new_doc = doc_merge(doc, other_doc, merge=merge)
    assert new_doc == {
        'a': {'b': {'c': {'d': (9, -9)}}},
        'c': {'d': 0},
        'b': {'c': (-1, {'d': 1})},
    }


def test_doc_update():
    other_doc = {
        'a': {'b': {'c': {'d': -9}}},
        'c': {'d': 0},
        'b': {'c': {'d': 1}},
        'd': {'e': 1},
    }

    new_doc = deepcopy(other_doc)
    doc_update(new_doc, doc)
    assert new_doc == {
        'a': {'b': {'c': {'d': 9}}},
        'b': {'c': -1},
        'c': {'d': 0},
        'd': {'e': 1},
    }

    new_doc = deepcopy(other_doc)
    doc_update(new_doc, doc, multival=True)
    assert new_doc == {
        'a': {'b': {'c': {'d': [-9, 9]}}},
        'b': {'c': [{'d': 1}, -1]},
        'c': {'d': 0},
        'd': {'e': 1},
    }


def test_doc_inherit_vector():
    doc = {
        'a': {
            'hello': 'world',
            'b': {
                'nothing': 'here',
                'c': {
                    'something': 'there',
                    'hello': 'friends',
                },
            },
        },
        'hello': 'there',
    }

    expected_inheritance = [
        ((), 'there'),
        (('a',), 'world'),
        (('a', 'b', 'c'), 'friends'),
    ]

    inheritance = doc_inherit_all(doc, ('a', 'b', 'c'), 'hello')
    assert inheritance == expected_inheritance


def test_doc_inherit():
    doc = {
        'a': {
            'hello': 'world',
            'b': {
                'nothing': 'here',
                'c': {
                    'something': 'there',
                    'hello': 'friends',
                },
            },
        },
        'hello': 'there',
    }

    assert doc_inherit(doc, ('a', 'b', 'c'), 'hello') == 'friends'
    assert doc_inherit(doc, ('a', 'b', 'c'), 'foo', default=9) == 9
    assert doc_inherit(doc, ('a', 'b', 'd'), 'hello') == 'world'
    assert doc_inherit(doc, ('z', 'd'), 'hello') == 'there'


def test_doc_inherit2():
    doc = {
        'a': {
            '.meta': {'hello': 'world'},
            'b': {
                'nothing': 'here',
                '.meta': {'other': 'earth'},
                'c': {
                    'something': 'there',
                    '.meta': {'hello': 'friends'},
                    'd': {
                        'other': 'there'
                    },
                },
            },
        },
        'hello': 'there',
    }

    assert doc_inherit2(doc, ('a', 'b', 'c'), ('.meta', 'hello')) == 'friends'
    assert doc_inherit2(doc, ('a', 'b', 'c'), ('foo',), default=9) == 9
    assert doc_inherit2(doc, ('a', 'b', 'c'), ('.meta', 'hello')) == 'friends'
    assert doc_inherit2(doc, ('a', 'b', 'd'), ('.meta', 'hello')) == 'world'
    assert doc_inherit2(doc, ('a', 'b', 'c', 'd'), ('.meta', 'hello')) == 'friends'

    assert doc_inherit2(doc, ('z', 'd'), ('hello',)) == 'there'

def test_doc_search_name():
    doc = {
        'hello': {
            'there': 'friend',
        },
        'there': 'exists',
        'nothing': {
            'is': 'there',
            'there': 'is',
        },
    }

    findings = doc_search_name(doc, 'there')
    findings.sort()
    assert findings == [
        ('hello', 'there'),
        ('nothing', 'there'),
        ('there',),
    ]


def test_doc_search_regex():
    doc = {
        'hello': {
            'there': 'friend',
        },
        'there': 'exists',
        'nothing': {
            'is': 'there',
            'there': 'is',
        },
    }

    findings = doc_search_regex(doc, '[erl]')
    findings.sort()
    assert findings == []

    findings = doc_search_regex(doc, '[hfni]')
    findings.sort()
    assert findings == [
        ('hello',),
        ('nothing',),
        ('nothing', 'is'),
    ]


def test_doc_from_ns():
    new_doc = doc_from_ns({
        'a/b/c/d': 9,
        'b/c': -1,
    })

    assert new_doc == doc

    new_doc = doc_from_ns({
        'a.b.c.d': 9,
        'b.c': -1,
    }, sep='.')

    assert new_doc == doc


def test_doc_to_ns():
    ns = doc_to_ns(doc)
    assert ns == {
        'a/b/c/d': 9,
        'b/c': -1,
    }

    ns = doc_to_ns(doc, sep='.')
    assert ns == {
        'a.b.c.d': 9,
        'b.c': -1,
    }


def test_random_doc():
    doc = random_doc()
    return doc


def test_doc_spec_get():
    test_doc = {
        'one': 1,
        '=': '=',
        'two': {'=': 2},
        'three': {'four': 4},
    }

    assert doc_spec_get(test_doc, 'foo', 9) == 9
    assert doc_spec_get(test_doc, 'foo') is None
    assert doc_spec_get(test_doc, 'two') == 2
    assert doc_spec_get(test_doc, 'one') == 1
    assert doc_spec_get(test_doc) == '='
    assert doc_spec_get(test_doc, 'four', 9) == 9


def test_doc_spec_set():
    test_doc = {}

    doc_spec_set(test_doc, 1)
    assert doc_spec_get(test_doc) == 1

    doc_spec_set(test_doc, 'one', 9)
    assert doc_spec_get(test_doc, 'one') == 9

    old_val = doc_spec_set(test_doc, 'one', 10)
    assert doc_spec_get(old_val) == 9


def test_doc_spec_iter():
    test_spec_source = {
        '=keys': ['four', 'three', '*', 'five*', '.two', '.one', '.six.*'],
        '.one': (),
        '.two': (),
        'three': (),
        'four': (),
        'five*': (),
        '.six.*': (),
        '*': (),
    }

    test_spec = doc_compile_spec(test_spec_source, predicates={})

    data = list(doc_spec_iter(test_spec))
    assert data == [
        ('four', ()),
        ('three', ()),
    ]

    data = list(doc_spec_iter(test_spec, what='_'))
    assert data == [
        ('four', ()),
        ('three', ()),
    ]

    data = list(doc_spec_iter(test_spec, what='.'))
    assert data == [
        ('.two', ()),
        ('.one', ()),
        ('.six', ()),
    ]

    data = list(doc_spec_iter(test_spec, what=''))
    assert data == []

    data = list(doc_spec_iter(test_spec, what='*'))
    assert data == []

    for what in ('*.', '*.'):
        data = list(doc_spec_iter(test_spec, what=what))
        assert data == [
            ('.two', ()),
            ('.one', ()),
            ('.six', ()),
            ('.six.*', ()),
        ]

    for what in ('_.', '._'):
        data = list(doc_spec_iter(test_spec, what=what))
        assert data == [
            ('four', ()),
            ('three', ()),
            ('.two', ()),
            ('.one', ()),
            ('.six', ()),
        ]

    for what in ('_*', '*_'):
        data = list(doc_spec_iter(test_spec, what=what))
        assert data == [
            ('four', ()),
            ('three', ()),
            ('*', ()),
            ('five*', ()),
        ]

    for what in ('.*_', '._*', '_.*', '_*.', '*._', '*_.'):
        data = list(doc_spec_iter(test_spec, what=what))
        assert data == [
            ('four', ()),
            ('three', ()),
            ('*', ()),
            ('five*', ()),
            ('.two', ()),
            ('.one', ()),
            ('.six', ()),
            ('.six.*', ()),
        ]


def test_doc_spec_merge():
    target_spec_source = {
        '*': (),
    }

    choice_spec_source = {
        '.choice': {},
    }

    activity_spec_source = {
        '.activity': (),
        '.choice': {
            '=': ['up', 'down', 'neutral'],
        },
    }

    affect_spec_source = {
        '.affect': (),
        '.choice': {
            '=': ['positive', 'negative', 'neutral'],
        },
        'intensity': (),
    }

    feeling_spec_source = {
        '.feeling': {},
        'activity': {
            '.activity': (),
        },
        'affect': {
            '.affect': (),
        },
    }

    color_spec_source = {
        '.color': (),
        '.feeling': (),
        'name': (),
    }

    register_specs = [
        ('.choice', choice_spec_source),
        ('.activity', activity_spec_source),
        ('.affect', affect_spec_source),
        ('.feeling', feeling_spec_source),
        ('.color', color_spec_source),
    ]

    color_config = {
        '.color': {},
    }

    sad_config = {
        '.feeling': {},
        'activity': {
            '=': 'down',
        },
        'affect': {
            '=': 'negative',
        },
    }

    blue_config = {
        'name': {
            '=': 'blue',
        },
        'affect': {
            'intensity': {
                '=': 'mild',
            },
        },
        '.foo': (),
    }

    predicates = {}
    errs = []

    target = {}
    errs = []
    target = doc_spec_merge(target, target_spec_source, predicates,
                            autoregister=False,
                            extend=True, merge=None,
                            loc=(), errs=errs)
    if errs:
        raise AssertionError(errs)

    for name, source in register_specs:
        errs = []
        doc_spec_merge({}, source, predicates,
                       autoregister=True,
                       extend=True, merge=None,
                       loc=(), errs=errs)
        if errs:
            report_errors(errs)
            raise AssertionError()

    configs = [
        color_config,
        sad_config,
        blue_config,
    ]

    for config in configs:
        errs = []
        doc_spec_merge(target, config, predicates,
                       autoregister=True,
                       extend=False, merge=None,
                       loc=(), errs=errs)
        if errs:
            report_errors(errs)
            raise AssertionError()

    expected_target = {
        '=d': ['.color', '.feeling', '.foo'],
        '=x': [''],
        '=k': ['*', '.color', '.feeling',
               'activity', 'affect', 'name', '.foo'],
        '.feeling': (),
        '.color': (),
        'activity': {
            '=d': ['.activity', '.choice'],
            '=x': (),
            '=k': ['.activity', '.choice'],
            '.activity': (),
            '.choice': {
                '=d': (),
                '=x': (),
                '=k': (),
                '=': ['up', 'down', 'neutral'],
            },
            '=': 'down',
        },
        'affect': {
            '=d': ['.affect', '.choice'],
            '=x': (),
            '=k': ['.affect', '.choice', 'intensity'],
            '.affect': (),
            '.choice': {
                '=d': (),
                '=x': (),
                '=k': (),
                '=': ['positive', 'negative', 'neutral'],
            },
            '=': 'negative',
            'intensity': {
                '=d': (),
                '=x': (),
                '=k': (),
                '=': 'mild',
            },
        },
        'name': {
            '=d': (),
            '=x': (),
            '=k': (),
            '=': 'blue',
        },
        '.foo': (),
        '*': (),
    }
    assert target == expected_target


def test_doc_spec_merge_dot_segments():
    predicates_org = {
        '.one': {
            '.one': {},
            'one': {},
        },

        '.one.two': {
            '.one.two': {},
            'one': {
                'two': {},
            },
        },
    }

    source = {
        '.one.two.*': {
            'strict': True,
        },
    }

    predicates = deepcopy(predicates_org)
    spec = doc_compile_spec(source, predicates)

    expected_spec = {
        '=d': ['.one', '.one.two', '.one.two.*'],
        '=k': ['.one', 'one', '.one.two', '.one.two.*'],
        '=x': ['.one.two.'],
        '.one': (),
        '.one.two': (),
        '.one.two.*': {
            '=d': (),
            '=k': ['strict'],
            '=x': (),
            'strict': {
                '=d': (),
                '=k': (),
                '=x': (),
                '=': True,
            },
        },
        'one': {
            '=d': (),
            '=k': ['two'],
            '=x': (),
            'two': (),
        },
    }

    # .one.two.* will also require
    # .one.two and .one as dependencies with empty body,
    # and will only apply 'strict' to .one.two.*
    assert spec == expected_spec

    source = {
        '=keys': ['.three.*'],
        '.three.*': {
            'boo': {},
        },
        '.three.four.*': {
            'strict': True,
        },
    }

    predicates = deepcopy(predicates_org)
    spec = doc_compile_spec(source, predicates)

    # .three.* will register
    #   .three with empty body and
    #   .three.* with 'boo'
    #
    # .three.four.* will
    #   skip .three since it has been processed by .three.*
    #   register .three.four with empty body
    #   register .three.four.* with 'strict'
    #
    # however, since '.three.four' is matched by '.three.*'
    # .three.four will acquire 'boo'
    # similarly, 'three.four.*' will acquire both 'strict' and 'boo'

    expected_spec = {
        '=d': ['.three', '.three.*', '.three.four', '.three.four.*'],
        '=k': ['.three', '.three.*', '.three.four', '.three.four.*'],
        '=x': ['.three.', '.three.four.'],
        '.three': (),
        '.three.*': {
            '=d': (),
            '=k': ['boo'],
            '=x': (),
            'boo': (),
        },
        '.three.four': {
            '=d': (),
            '=k': ['boo'],
            '=x': (),
            'boo': (),
        },
        '.three.four.*': {
            '=d': (),
            '=k': ['boo', 'strict'],
            '=x': (),
            'boo': (),
            'strict': {
                '=d': (),
                '=k': (),
                '=x': (),
                '=': True,
            },
        },
    }
    assert spec == expected_spec

    source = {
        '=keys': ['.three.four', '*'],
        '.three.four': {
            'hi': {},
        },
        '*': {
            'boo': {},
        },
        '.three.four.five.*': {
            'strict': True,
        },
    }

    predicates = deepcopy(predicates_org)
    spec = doc_compile_spec(source, predicates)

    # .three.four will register
    #   .three as empty
    #   .three.four with 'hi'
    #
    # .three.four.* will skip .three and .three.four
    # but register .three.four.five as empty and
    # .three.four.five.* with 'strict'.
    #
    # because of '*',
    # both .three.four.five and .three.four.five.* will
    # acquire 'boo'

    expected_spec = {
        '=d': ['.three', '.three.four', '.three.four.five', '.three.four.five.*'],
        '=k': ['.three', '.three.four', '*', '.three.four.five', '.three.four.five.*'],
        '=x': ['', '.three.four.five.'],
        '.three': (),
        '.three.four': {
            '=d': (),
            '=k': ['hi'],
            '=x': (),
            'hi': (),
        },
        '*': {
            '=d': (),
            '=k': ['boo'],
            '=x': (),
            'boo': (),
        },
        '.three.four.five': {
            '=d': (),
            '=k': ['boo'],
            '=x': (),
            'boo': (),
        },
        '.three.four.five.*': {
            '=d': (),
            '=k': ['boo', 'strict'],
            '=x': (),
            'boo': (),
            'strict': {
                '=d': (),
                '=k': (),
                '=x': (),
                '=': True,
            },
        },
    }

    assert spec == expected_spec


def test_doc_spec_merge_prefixes():
    spec = {
        'a*': {'=': 'a'},
        'ab*': {'=': 'ab'},
        'abc*': {'=': 'abc'},
        'b*': {'=': 'b'},
    }

    config = {
        'a': {'=': 'a'},
        'ab': {'=': 'ab'},
        'abc': {'=': 'abc'},
        'abd': {'=': 'ab'},
        'ac': {'=': 'a'},
    }

    doc_spec_config(spec, config, predicates={})


construction_context = {
        'instance': {},
        'loc': (),
        'top_spec': {},
        'predicate': '.something',
        'predicates': {},
        'constructors': {},
        'constructed': set(),
        'round': 0,
        'errs': {},
        'context': None,
    }


def test_make_constructor():

    def valid_constructor(
        instance,
        loc,
        round,
        top_spec,
        predicate,
        predicates,
        constructors,
        constructed,
        errs,
        context,
    ):
        pass

    def invalid_constructor(boohoo):
        pass

    make_constructor(valid_constructor)(construction_context)

    try:
        make_constructor(invalid_constructor)
    except InvalidInput:
        pass
    else:
        m = "InvalidInput not raised!"
        raise AssertionError(m)

    class ClassConstructor(object):
        def __call__(self, instance, loc, context):
            pass

    make_constructor(ClassConstructor())(construction_context)


def test_doc_compile_spec():

    original_spec_doc = {
        '=keys': ['.two'],
        'one': 1,
        '.two': {},
        '.three': {},
        'four': {
            '=keys': ['.five', '.six', '*'],
            '.five': {},
            '.six': {},
            'seven': 7,
            '*': (),
        },
        'eight': 8,
    }

    predicates = {
        '.two': {'=d': (), '=k': ()},
        '.three': {'=d': (), '=k': ['*'], '*': {}},
        '.five': {'=d': (), '=k': ()},
    }

    ok = False
    try:
        spec_doc = doc_compile_spec(original_spec_doc, predicates,
                                    autoregister=False)
    except Error as e:
        ok = True
    except Exception as e:
        pass

    if not ok or not any(
        (
            isinstance(x, MergeFault)
            and x.what == 'no-predicate'
            and x.kwargs.get('data') == '.six'
        ) for x in e.errs
    ):
        m = "MergeFault(what='no-predicate', data='.six') not raised"
        raise AssertionError(m)

    spec_doc = doc_compile_spec(original_spec_doc, predicates,
                                autoregister=True)

    expected_spec_doc = {
        '=d': ['.two', '.three'],
        '=k': ['.two', '.three', '*', 'eight', 'four', 'one'],
        '=x': [''],
        'one': {
            '=d': (),
            '=x': (),
            '=k': (),
            '=': 1,
        },
        '.two': (),
        '.three': (),
        'four': {
            '=d': ['.five', '.six'],
            '=k': ['.five', '.six', '*', 'seven'],
            '=x': [''],
            '.five': (),
            '.six': (),
            'seven': {
                '=d': (),
                '=x': (),
                '=k': (),
                '=': 7,
            },
            '*': (),
        },
        'eight': {
            '=d': (),
            '=x': (),
            '=k': (),
            '=': 8,
        },
        '*': (),
    }

    assert spec_doc == expected_spec_doc


def test_doc_strip_spec():
    original_doc = {
        'one': None,
        'two': {
            '.something': {},
            '=': 1,
        },
        'three': {
            'four': 4,
            'five': {},
        },
    }

    predicates = {
        '.something': {
            '.something': {},
            '=k': ['.something'],
            '=d': (),
        },
    }

    spec_doc = doc_compile_spec(original_doc, predicates)
    stripped_doc = doc_strip_spec(spec_doc)
    expected_doc = {
        'one': None,
        'two': 1,
        'three': {
            'four': 4,
            'five': {},
        },
    }
    assert stripped_doc == expected_doc


def test_doc_spec_register():
    check_object = object()

    def constructor_fn(instance, loc):
        return check_object

    predicates = {}
    constructors = {}

    spec_source = {
        '.hellospec': {},
        'hello': {
            '=': 'world',
        },
    }

    doc_spec_register_predicate(predicates, '.spec', spec_source)
    doc_spec_register_constructor(constructors, '.spec', constructor_fn)

    something_source = {'.spec': ()}

    doc_spec_register_predicate(predicates, '.something', something_source)
    doc_spec_register_constructor(constructors, '.something', constructor_fn)

    something_spec = doc_compile_spec(something_source, predicates=predicates)

    assert predicates['.something'] == something_source
    assert constructors['.something'](construction_context) is check_object

    another_spec = {
        '=keys': ['.an.other.spec.*', '.spec'],
        '.an.other.spec.*': {},
        '.spec': {},
    }

    doc_compile_spec(another_spec, predicates, autoregister=True)
    assert (
        predicates['.an'] ==
        predicates['.an.other'] ==
        predicates['.an.other.spec'] ==
        predicates['.an.other.spec.*']
    )


def test_doc_spec_config():
    text_spec = {
        '.text': {},
    }

    address_spec = {
        '.address': {},
    }

    person_spec = {
        '.person': {},
        '=keys': ['name', 'address', 'notes'],
        'name': {'.text': {}},
        'address': {'.address': {}},
        'notes': {
            '*': {'.text': {}},
        },
    }

    def constructor(context):
        pass

    predicates = {}
    constructors = {}

    doc_spec_register_predicate(predicates, '.text', text_spec)
    doc_spec_register_constructor(constructors, '.text', constructor)

    doc_spec_register_predicate(predicates, '.address', address_spec)
    doc_spec_register_constructor(constructors, '.address', constructor)

    doc_spec_register_predicate(predicates, '.person', person_spec)
    doc_spec_register_constructor(constructors, '.person', constructor)

    spec_source = {
        'husband': {'.person': {}},
        'wife': {'.person': {}},
        'problems': {},
        '*': {
            'adventure': {},
        },
    }

    spec_doc = doc_compile_spec(spec_source, predicates)

    config_error_doc = {
        'nothing': None,
    }
    try:
        doc_spec_config(spec_doc, config_error_doc, predicates)
    except Error as e:
        errs = e.errs
        assert (
            len(errs) == 1 and
            isinstance(errs[0], MergeFault) and
            errs[0].loc == () and
            errs[0].what == 'cannot-disable' and
            errs[0].kwargs.get('data') == 'nothing'
        )

    config0_doc = {
        'problems': None,
        '*': None,
    }

    spec_doc1 = doc_spec_config(spec_doc, config0_doc, predicates)

    config1_doc = {
        'wife': {
            'name': {'=': 'mary'},
        },
        'husband': {
            'name': {'=': 'jesus'},
        },
    }

    spec_doc2 = doc_spec_config(spec_doc1, config1_doc, predicates)

    config2_doc = {
        'wife': {
            'address': {'=': 'earth'},
            'notes': ['nice', 'happy'],
        },
        'husband': {
            'address': {'=': 'sky'},
        },
    }

    spec_doc3 = doc_spec_config(spec_doc2, config2_doc, predicates)

    expected_doc = {
        '=d': (),
        '=x': (),
        '=k': ['husband', 'problems', 'wife'],
        'husband': {
            '=d': ['.person'],
            '=x': (),
            '=k': ['.person', 'name', 'address', 'notes'],
            '.person': (),
            'name': {
                '=d': ['.text'],
                '=x': (),
                '=k': ['.text'],
                '.text': (),
                '=': 'jesus',
            },
            'address': {
                '=d': ['.address'],
                '=x': (),
                '=k': ['.address'],
                '.address': (),
                '=': 'sky',
            },
            'notes': {
                '=d': (),
                '=k': ['*'],
                '=x': [''],
                '*': {
                    '.text': (),
                    '=d': ['.text'],
                    '=k': ['.text'],
                    '=x': (),
                },
            },
        },
        'wife': {
            '=d': ['.person'],
            '=x': (),
            '=k': ['.person', 'name', 'address', 'notes'],
            '.person': (),
            'name': {
                '=d': ['.text'],
                '=k': ['.text'],
                '=x': (),
                '=': 'mary',
                '.text': (),
            },
            'address': {
                '=d': ['.address'],
                '=k': ['.address'],
                '=x': (),
                '.address': (),
                '=': 'earth',
            },
            'notes': {
                '=d': (),
                '=k': ['*', 'nice', 'happy'],
                '=x': [''],
                '*': {
                    '.text': (),
                    '=d': ['.text'],
                    '=k': ['.text'],
                    '=x': (),
                },
                'nice': {
                    '.text': (),
                    '=d': ['.text'],
                    '=k': ['.text'],
                    '=x': (),
                },
                'happy': {
                    '.text': (),
                    '=d': ['.text'],
                    '=k': ['.text'],
                    '=x': (),
                },
            },
        },
        'problems': None,
    }

    assert spec_doc3 == expected_doc


def test_doc_spec_construct():

    integer_spec = {
        '.integer': {},
    }

    def integer_constructor(instance):
        instance['='] = int(instance['='])

    instance_spec = {
        'number': {
            '.integer': {},
        },
    }

    config = {
        'number': '9',
    }

    predicates = {}
    constructors = {}

    doc_spec_register_predicate(predicates, '.integer', integer_spec)
    doc_spec_register_constructor(constructors, '.integer',
                                  integer_constructor)

    doc_compile_spec(instance_spec, predicates)
    doc_compile_spec(config, predicates)
    instance = doc_spec_config(instance_spec, config, predicates)
    doc_spec_construct(instance, predicates, constructors)

    expected_instance = {
        '=d': (),
        '=x': (),
        '=k': ['number'],
        'number': {
            '=d': ['.integer'],
            '=x': (),
            '=k': ['.integer'],
            '.integer': {},
            '=': 9,
        },
    }

    assert instance == expected_instance


def test_doc_construct():
    integer_spec = {
        '.integer': {},
    }

    def integer_constructor(instance):
        instance['='] = int(instance['='])

    instance_spec = {
        'number': {
            '.integer': {},
        },
    }

    config = {
        'number': '9',
    }

    predicates = {}
    constructors = {}

    doc_spec_register_predicate(predicates, '.integer', integer_spec)
    doc_spec_register_constructor(constructors, '.integer',
                                  integer_constructor)

    instance = doc_construct(instance_spec, config, predicates, constructors)

    expected_instance = {
        '=d': (),
        '=x': (),
        '=k': ['number'],
        'number': {
            '=d': ['.integer'],
            '=x': (),
            '=k': ['.integer'],
            '.integer': {},
            '=': 9,
        },
    }

    assert instance == expected_instance


def test_constructor_order():
    call_log = []

    def first_constructor(context):
        call_log.append('.one')

    def second_constructor(context):
        construct_after(context, '.one')
        call_log.append('.two')

    def third_constructor(context):
        construct_after(context, '.one', '.two')
        call_log.append('.three')

    def last_constructor(context):
        construct_last(context)
        call_log.append('.four')

    spec_source = {
        '=keys': ['.four', '.three', '.two', '.one'],
        '.one': {},
        '.two': {},
        '.three': {},
        '.four': {},
    }

    predicates = {}
    constructors = {}

    spec = doc_compile_spec(spec_source, predicates)
    for k, v in [
        ('.one', first_constructor),
        ('.two', second_constructor),
        ('.three', third_constructor),
        ('.four', last_constructor),
    ]:
        doc_spec_register_constructor(constructors, k, v)

    doc_spec_construct(spec, predicates, constructors)
    expected_call_log = ['.one', '.two', '.three', '.four']
    assert call_log == expected_call_log


def test_non_shared_meta():
    from docular.spec import doc_spec_registry_verify_non_shared_meta
    spec_source = {
        '.spec.*': {},
    }

    spec_a_source = {
        '.spec.a': {},
    }

    predicates = {}

    spec = doc_compile_spec(spec_source, predicates)
    spec_a = doc_compile_spec(spec_a_source, predicates)

    doc_spec_config(spec, spec_a, predicates)

    doc_spec_registry_verify_non_shared_meta(predicates)

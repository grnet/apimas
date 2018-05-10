from docular import (
    doc_spec_register_predicate,
    doc_spec_register_constructor,
    doc_construct,
    make_constructor,
    Error,
)


integer_spec = {
    '.integer': {},
}


def construct_integer(instance, context):
    val = instance['=']
    if isinstance(val, basestring):
        instance['='] = int(val)
    elif not isinstance(val, (long, int)):
        m = '{val!r} is not an integer'.format(val=val)
        raise Error(m)


text_spec = {
    '.text': {},
}


def construct_text(instance, context):
    val = instance['=']
    if not isinstance(val, basestring):
        instance['='] = str(val)


predicates = {}
constructors = {}


doc_spec_register_predicate(predicates, '.integer', integer_spec)
doc_spec_register_constructor(constructors, '.integer', construct_integer)

doc_spec_register_predicate(predicates, '.text', text_spec)
doc_spec_register_constructor(constructors, '.text', construct_text)


def test_construction():
    spec = {
        'integer': {
            '.integer': {},
        },
        'text': {
            '.text': {},
        },
    }

    config = {
        'integer': '9',
        'text': -9,
    }

    instance = doc_construct(spec, config, predicates, constructors)
    expected_instance = {
        '=d': (),
        '=x': (),
        '=k': ['integer', 'text'],
        'integer': {
            '=d': ['.integer'],
            '=x': (),
            '=k': ['.integer'],
            '.integer': {},
            '=': 9,
        },
        'text': {
            '=d': ['.text'],
            '=x': (),
            '=k': ['.text'],
            '.text': {},
            '=': '-9',
        },
    }
    assert instance == expected_instance


def test_construction_config():
    spec = {
        ':affiliation': {
            '=': 'none',
            'role': 'none',
        },
        ':flag': True,
        'game': {
            'judges': {
                '*': {
                    '.*': {},
                    ':*': {},
                    'name': {'.text': {}},
                    ':affiliation': {
                        '.text': {},
                        'role': {},
                    },
                    ':flag': {},
                },
            },
            'teams': {
                ':affiliation': 'fufu',
                '*': {
                    '.*': {},
                    ':*': {},
                    'name': {'.text': {}},
                    ':affiliation': {},
                    ':flag': False,
                },
            },
            'players': {
                ':affiliation': {
                    '=': 'bozo',
                    'rank': 'soldier',
                },
                '*': {
                    '.*': {},
                    ':*': {},
                    'name': {'.text': {}},
                    'team': {'.text': {}},
                    ':affiliation': {
                        '.text': {},
                        'rank': {},
                        '*': {},
                    },
                },
            },
        },
    }

    config = {
        'game': {
            'judges': {
                'foo': {
                    '.foo': {},
                    'name': 'foo',
                },
                'bar': {
                    '.bar': {},
                    'name': 'bar',
                    ':affiliation': {
                        '=': 'bar',
                        'role': {},
                    },
                },
            },
            'teams': {
                'teamfoo': {
                    '.teamfoo': {},
                    'name': 'teamfoo',
                },
                'teambar': {
                    '.teambar': {},
                    'name': 'teambar',
                    ':affiliation': 'teambar',
                },
            },
            'players': {
                'jack': {
                    '.jack': {},
                    'name': 'jack',
                    'team': 'teamfoo',
                    ':flag': {},
                },
                'jill': {
                    '.jill': {},
                    'name': 'jill',
                    'team': 'teambar',
                    ':affiliation': 'jaju',
                    ':flag': False,
                },
                'jova': {
                    '.jova': {},
                    'name': 'jova',
                    'team': 'teamoops',
                    ':flag': True,
                    ':affiliation': {
                        'role': {},
                        'rank': 'centurion',
                        '=': 'jovafu',
                    },
                },
            },
        },
    }

    predicates = {
        '.*': {},
        '.text': {},
        '.foo': {},
        '.bar': {},
        '.teamfoo': {},
        '.teambar': {},
        '.jack': {},
        '.jill': {},
        '.jova': {},
    }

    @make_constructor
    def construct_nothing(instance):
        pass

    @make_constructor
    def construct_text(instance, config):
        assert not [x for x in config if not x[:1] == '=']

    @make_constructor
    def construct_foo(instance, config):
        # from / and /game/judges
        assert config[':affiliation']['='] == 'none'
        assert not config[':affiliation']['.text']
        assert config[':affiliation']['role']['='] == 'none'

        # from /
        assert config[':flag']['='] is True

    @make_constructor
    def construct_bar(instance, config):
        # from / and /game/judges
        assert config[':affiliation']['='] == 'bar'
        assert not config[':affiliation']['.text']
        assert config[':affiliation']['role']['='] == 'none'

        # from /
        assert config[':flag']['='] is True

    @make_constructor
    def construct_teamfoo(instance, config):
        # from /game/teams
        assert config[':affiliation']['='] == 'fufu'

        # from /
        assert config[':affiliation']['role']['='] == 'none'

        # from /game/teams
        assert config[':flag']['='] is False

    @make_constructor
    def construct_teambar(instance, config):
        # from /game/teams/teambar
        assert config[':affiliation']['='] == 'teambar'

        # from /
        assert config[':affiliation']['role']['='] == 'none'

        assert '.text' not in config[':affiliation']

        # from /game/teams
        assert config[':flag']['='] is False


    @make_constructor
    def construct_jack(instance, config):
        # from /game/players
        assert config[':affiliation']['='] == 'bozo'
        assert config[':affiliation']['rank']['='] == 'soldier'

        # from /
        assert config[':affiliation']['role']['='] == 'none'

        # matched from /game/players/*
        assert '.text' in config[':affiliation']

        # from /
        assert config[':flag']['='] is True

    @make_constructor
    def construct_jill(instance, config):
        # from /game/players/jill
        assert config[':affiliation']['='] == 'jaju'

        # from /game/players
        assert config[':affiliation']['rank']['='] == 'soldier'

        # from /
        assert config[':affiliation']['role']['='] == 'none'

        # matched from /game/players/*
        assert '.text' in config[':affiliation']

        # from /game/players/jill
        assert config[':flag']['='] is False


    @make_constructor
    def construct_jova(instance, config):
        # from /game/players/jova
        assert config[':affiliation']['='] == 'jovafu'
        assert config[':affiliation']['rank']['='] == 'centurion'

        # from /
        assert config[':affiliation']['role']['='] == 'none'

        # matched from /game/players/*
        assert '.text' in config[':affiliation']

        # from /
        assert config[':flag']['='] is True

    constructors = {
        '.*': construct_nothing,
        '.text': construct_text,
        '.foo': construct_foo,
        '.bar': construct_bar,
        '.teamfoo': construct_teamfoo,
        '.teambar': construct_teambar,
        '.jack': construct_jack,
        '.jill': construct_jill,
        '.jova': construct_jova,
    }

    instance = doc_construct(spec, config, predicates, constructors)

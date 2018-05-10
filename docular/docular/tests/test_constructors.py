from docular import doc_construct, ValidationError, Error
from docular.constructors import predicates, constructors
from copy import deepcopy


spec = {
    'date': {
        '.text': {
            'regex': '[0-9]{4}-[0-9]{2}-[0-9]{2}',
        },
    },
    'priority': {
        '.integer': {
            'min': 0,
            'max': 100,
        },
    },
    'name': {
        '.text': {
            'maxlen': '32',
            'encoding': 'utf-8',
            'excluded': '`~!@#$%^&*()-_=+[]{};:\'"\\|,.<>',
        },
    },
    'callsign': {
        '.text': {
            'minlen': '3',
            'maxlen': '7',
            'alphabet': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        },
    },
    'datetime': {
        '.object': {},
        'class': 'datetime:datetime',
        'args': {
            'year': {
                '.integer': {},
            },
            'month': {
                '.integer': {
                    'min': 1,
                    'max': 12,
                },
            },
            'day': {
                '.integer': {
                    'min': 1,
                    'max': 31,
                },
            },
        },
    },
}


config = {
    'date': '2017-09-18',
    'priority': '100',
    'name': 'blackbad',
    'callsign': 'BBAD',
    'datetime': {
        'args': {
            'year': 2017,
            'month': 9,
            'day': 22,
        },
    },
}


def test_generic():
    ok_config = deepcopy(config)
    ok_spec = deepcopy(spec)
    instance = doc_construct(ok_spec, ok_config, predicates, constructors)
    instance
    # import pprint
    # pprint.pprint(instance)

    err_cases = (
        ('date', '17-09-18'),
        ('priority', '101'),
        ('priority', '-1'),
        ('name', 'z' * 33),
        ('name', 'oops!'),
        ('callsign', 'AA'),
        ('callsign', 'ABz'),
        ('datetime', 999),
    )

    for key, val in err_cases:
        err_spec = deepcopy(spec)
        err_config = deepcopy(config)
        err_config[key] = val
        try:
            instance = doc_construct(err_spec, err_config,
                                     predicates, constructors)
            instance
        except Error as e:
            assert len(e.errs) == 1
            assert e.errs[0].loc == (key,)
        else:
            m = "{key!r} = {val!r} should not have been accepted!"
            m = m.format(key=key, val=val)
            raise AssertionError(m)

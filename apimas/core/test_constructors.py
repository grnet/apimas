# XXX: temporary test file until we have proper unit testing

from documents import *
from constructors import *
from pprint import pprint


collection_id_spec = {
    '.integer': {'min': 0},
    '.initwrite': {},
    '.primary': {},
}

signature_spec = {
    'signer': {
        'key': { '.blob': {} },
        'key_type': { '.text': {} },
    },
    'text_hash': { '.blob': {} },
    'text_hash_type': { '.text': {} },
    'cryptodata': { '.blob': {} },
}

contribution_data_spec = {
    'id': collection_id_spec,
    'text': {
        'body': {
            '.blob': {},
        },
        'signers': {
            '*': {
                'key': { '.blob': {} },
            },
        },
        'accept': { '.boolean': {} },
    },
    'signature': signature_spec,
}

contribution_actions_spec = {
    'list': { '.action': {} },
    'create': { '.action': {} },
    'retrieve': { '.action': {} },
}

negotiation_actions_spec = {
    'list': { '.action': {} },
    'create': { '.action': {} },
    'retrieve': { '.action': {} },
    'update': { '.action': {} },
    'replace': { '.action': {} },
}

spec = {
    'negotiation': {
        '.collection': {},
        '*': {
            'data': {
                'id': collection_id_spec,
                'status': {
                    '.text': {
                        '.choices': {
                            'pending': {},
                            'concluded': {},
                            'abandoned': {}
                        },
                    },
                    '.index': {},
                    '.readonly': {},
                },
                'consensus_id': {
                    '.string': {},
                    '.index': {},
                    '.readonly': {},
                    '.reference': {
                        '.target': 'consensus',
                    },
                },
                'contribution': {
                    '.collection': {},
                    'actions': contribution_actions_spec,
                    '*': {
                        'data': contribution_data_spec, 
                    },
                },
            },
            'actions': negotiation_actions_spec,
        },
    },
}

instance = doc_construct({}, spec, autoconstruct=True, constructors={})
pprint(instance, indent=2)


match_spec = {
    'hello*': {
        'boo': {},
    },
    'hell*': 'goo',
    '*': {
        'zoo': {},
    },
}


test_keys = ['hel', 'hell', 'hella', 'hello_world']
for key in test_keys:
    instance = doc_construct({key: {}}, match_spec, autoconstruct=True)
    pprint({'key': instance[key]}, indent=2)

pprint(instance, indent=2)


example_spec = {
    'products': {
        '.collection': {},
        'id-*': {
            '.resource': {},
            'data-*': {
                'stock': { '.integer', '.blankable', '.readonly' },
                'name': {
                    '.field': {'field_type': 'string'},
                    '.blankable': {}
                }
            }
        }
    }
}

instance = doc_construct({}, example_spec,
                         autoconstruct=True, constructors={})
pprint(instance, indent=2)


def construct_alpha(instance, spec, loc, context):
    assert doc_get(context['top_spec'], loc) == spec
    instance['alpha'] = spec['val']
    if 'beta' not in instance:
        assert context['cons_round'] == 0
        assert '.beta' not in context['constructed']
        raise DeferConstructor
    assert context['cons_round'] <= 1
    return instance


register_constructor(construct_alpha, name='alpha')


def construct_beta(instance, spec, loc, context):
    assert doc_get(context['top_spec'], loc) == spec
    instance['beta'] = spec['val']
    if 'alpha' not in instance:
        assert context['cons_round'] == 0
        assert '.alpha' not in context['constructed']
        raise DeferConstructor
    if context['cons_round'] == 0:
        raise DeferConstructor
    assert context['cons_round'] == 1
    assert '.alpha' in context['constructed']
    instance['gamma'] = instance['alpha'], instance['beta']
    return instance


register_constructor(construct_beta, name='beta')


defer_spec = {
    '.alpha': {'val': 'hello'},
    '.beta': {'val': '!'},
}

instance = doc_construct({}, defer_spec, autoconstruct=True)
pprint(instance, indent=2)


@register_constructor
def construct_deadlock1(instance, spec, loc, context):
    assert doc_get(context['top_spec'], loc) == spec
    instance['deadlock'] = 0
    raise DeferConstructor


@register_constructor
def construct_deadlock2(instance, spec, loc, context):
    assert doc_get(context['top_spec'], loc) == spec
    instance['deadlock'] = 1
    raise DeferConstructor


deadlock_spec = {
    '.deadlock1': {},
    '.deadlock2': {},
}

try:
    instance = doc_construct({}, deadlock_spec, autoconstruct=True)
except InvalidInput as e:
    print e


simple_spec = {
    'name': {
        '.text': {
            'minlen': 6,
            'maxlen': 32,
        },
    },
    'age': {
        '.integer': {
            '.min': 18,
            '.max': 65,
        },
    },
}


def randomizer(instance, spec, loc, context):
    key = loc[-1]
    instance[key] = spec
    if loc[-1].startswith('.') and type(spec) is dict:
        instance[key]['.randomize'] = {}
    return instance


randomized_spec = doc_construct({}, simple_spec,
                                autoconstruct='randomizer',
                                constructors={'randomizer': randomizer})
pprint(randomized_spec, indent=2)


randomized_instance = doc_construct({}, simple_spec)
pprint(randomized_instance, indent=2)

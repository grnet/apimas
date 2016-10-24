from documents import *
from constructors import *
import json


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
print json.dumps(instance, indent=2)


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
    print json.dumps({'key': instance[key]}, indent=2)

print json.dumps(instance, indent=2)


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
print json.dumps(instance, indent=2)


@register_constructor
def construct_alpha(instance, spec, loc):
    instance['alpha'] = spec['val']
    if 'beta' not in instance:
        return DEFER_CONSTRUCTOR
    instance['gamma'] = instance['alpha'], instance['beta']
    return instance

@register_constructor
def construct_beta(instance, spec, loc):
    instance['beta'] = spec['val']
    if 'beta' not in instance:
        return DEFER_CONSTRUCTOR
    instance['gamma'] = instance['alpha'], instance['beta']
    return instance


defer_spec = {
    '.alpha': {'val': 'hello'},
    '.beta': {'val': '!'},
}

instance = doc_construct({}, defer_spec, autoconstruct=True)
print json.dumps(instance, indent=2)


@register_constructor
def construct_deadlock1(instance, spec, loc):
    instance['deadlock'] = 0
    return DEFER_CONSTRUCTOR


@register_constructor
def construct_deadlock2(instance, spec, loc):
    instance['deadlock'] = 1
    return DEFER_CONSTRUCTOR


deadlock_spec = {
    '.deadlock1': {},
    '.deadlock2': {},
}

instance = doc_construct({}, deadlock_spec, autoconstruct=True)

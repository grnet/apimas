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
    instance = doc_construct({key: {}}, spec, autoconstruct='.autoconstruct')
    print json.dumps({'key': instance[key]}, indent=2)

print json.dumps(instance, indent=2)


example_spec = {
    'products': {
        '.collection': {},
        'id-*': {
            '.resource': {},
            'data-*': {
                'stock': {
                    '.integer': {},
                    '.blankable': {},
                    '.readonly': {}
                },
                'name': {
                    '.field': {'field_type': 'string'},
                    '.blankable': {}
                }
            }
        }
    }
}

instance = doc_construct({}, example_spec, autoconstruct='.autoconstruct')
print json.dumps(instance, indent=2)

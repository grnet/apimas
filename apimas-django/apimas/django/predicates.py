import docular

PREDICATES = {}
def register_predicate(predicate, spec):
    docular.doc_spec_register_predicate(PREDICATES, predicate, spec)


def register_base_predicate(predicate):
    register_predicate(predicate, {predicate: {}})


register_base_predicate('.boolean')
register_base_predicate('.string')

handler_spec = {'.handler': {}, '.string': {}}
register_predicate('.handler', handler_spec)

register_base_predicate('.flag.*')
register_base_predicate('.flag.readonly')

register_base_predicate('.fields')

field_spec = {'.field.*': {},
              'source': {'.string': {}},
              '.flag.*': {},
              '*': {},
}
register_predicate('.field.*', field_spec)

register_base_predicate('.field.string')
register_base_predicate('.field.serial')

field_identity_spec = {'.field.identity': {'to': {'.string': {}}}}
register_predicate('.field.identity', field_identity_spec)

register_base_predicate('.meta')

field_collection_spec = {
    '.field.collection.*': {},
    'actions': {
        '.action-template.*': {},
        '*': {
            ".action": {},
            'on_collection': {'.boolean': {}},
            'method': {'.string': {}},
            'url': {'.string': {}},
            'handler': {".handler": {}},
            'pre': {"*": {".handler": {}}},
            'post': {"*": {".handler": {}}},
        }
    },
    'fields': {'*': {".field.*": {}}},
    '*': {},
}
register_predicate('.field.collection.*', field_collection_spec)

apimas_app_spec = {
    '.apimas_app': {},
    '.meta': {},
    '*': {
        ".endpoint": {},
        ".meta": {},
        "*": {'.field.collection.*': {}},
    },
}
register_predicate('.apimas_app', apimas_app_spec)

field_collection_django_spec = {
    '.field.collection.django': {},
    'model': {'.string': {}},
    'bound': {'.string': {}},
}
register_predicate('.field.collection.django', field_collection_django_spec)

action_template_django_create_spec = {
    '.action-template.django.create': {},
    'create': {
        'method': 'POST',
        'on_collection': True,
        'url': '/',
        'handler': 'apimas.django.handlers.CreateHandler',
        'pre': {
#            '1': 'apimas.components.processors.Authentication',
#            '2': 'apimas.django.processors.UserRetrieval',
            '3': 'apimas.django.processors.Permissions',
            '4': 'apimas.components.processors.DeSerialization',
            '5': 'apimas.components.processors.CerberusValidation',
        },
        'post': {
            '1': 'apimas.django.processors.InstanceToDict',
            '2': 'apimas.components.processors.Serialization'
        },
    },
}
register_predicate('.action-template.django.create',
                   action_template_django_create_spec)


action_template_django_list_spec = {
    '.action-template.django.list': {},
    'list': {
        'method': 'GET',
        'on_collection': True,
        'url': '/',
        'pre': {
#            '1': 'apimas.components.processors.Authentication',
#            '2': 'apimas.django.processors.UserRetrieval',
            '3': 'apimas.django.processors.Permissions',
        },
        'handler': 'apimas.django.handlers.ListHandler',
        'post': {
#            '1': 'apimas.django.processors.Filtering',
            '2': 'apimas.django.processors.InstanceToDict',
            '3': 'apimas.components.processors.Serialization',
        }
    },
}
register_predicate('.action-template.django.list',
                   action_template_django_list_spec)


action_template_django_retrieve_spec = {
    '.action-template.django.retrieve': {},
    'retrieve': {
        'method': 'GET',
        'on_collection': False,
        'url': '/',
        'pre': {
#            '1': 'apimas.components.processors.Authentication',
#            '2': 'apimas.django.processors.UserRetrieval',
#            '3': 'apimas.django.processors.ObjectRetrieval',
            '4': 'apimas.django.processors.Permissions',
        },
        'handler': 'apimas.django.handlers.RetrieveHandler',
        'post': {
            '1': 'apimas.django.processors.InstanceToDict',
            '2': 'apimas.components.processors.Serialization',
        }
    },
}

register_predicate('.action-template.django.retrieve',
                   action_template_django_retrieve_spec)

# PREDICATES =  {
#     '.action-template.django.update': {
#         '.action-template.django.update': {},
#         'update': {
#             'method': 'PUT',
#             'url': '/',
#             'pre': [
#                 'apimas.components.processors.Authentication',
#                 'apimas.django.processors.UserRetrieval',
#                 'apimas.django.processors.ObjectRetrieval',
#                 'apimas.django.processors.Permissions',
#                 'apimas.components.processors.DeSerialization',
#                 'apimas.components.processors.CerberusValidation',
#             ],
#             'handler': 'apimas.django.handlers.UpdateHandler',
#             'post': [
#                 'apimas.django.processors.InstanceToDict',
#                 'apimas.components.processors.Serialization',
#             ]

#         },
#     },
#     '.action-template.django.partial_update': {
#         '.action-template.django.partial_update': {},
#         'partial_update': {
#             'method': 'PATCH',
#             'url': '/',
#             'pre': [
#                 'apimas.components.processors.Authentication',
#                 'apimas.django.processors.UserRetrieval',
#                 'apimas.django.processors.ObjectRetrieval',
#                 'apimas.django.processors.Permissions',
#                 'apimas.components.processors.Serialization',
#             ],
#             'handler': 'apimas.django.handlers.UpdateHandler',
#             'post': [
#                 'apimas.django.processors.InstanceToDict',
#                 'apimas.components.processors.Serialization',
#             ]

#         },
#     },
#     '.action-template.django.delete': {
#         '.action-template.django.delete': {},
#         'delete': {
#             'method': 'DELETE',
#             'url': '/',
#             'pre': [
#                 'apimas.components.processors.Authentication',
#                 'apimas.django.processors.UserRetrieval',
#                 'apimas.django.processors.ObjectRetrieval',
#                 'apimas.django.processors.Permissions',
#             ],
#             'handler': 'apimas.django.handlers.DeleteHandler',
#         },
#     }
# }


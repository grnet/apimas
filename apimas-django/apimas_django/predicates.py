import docular

spec_list = [
    {'.boolean': {}},
    {'.string': {}},
    {'.integer': {}},
    {'.float': {}},

    {'.handler': {}, '.string': {}},

    {'.flag.*': {}},
    {'.flag.readonly': {}},
    {'.flag.nullable': {}},
    {'.flag.filterable': {}},

    {'.resource': {}},

    {
        '.field.*': {},
        'source': {'.string': {}},
        '.flag.*': {},
        '*': {},
    },

    {'.field.string': {}},
    {'.field.serial': {}},
    {'.field.integer': {}},
    {'.field.float': {}},
    {'.field.identity': {'to': {'.string': {}}}},
    {'.field.uuid': {}},
    {'.field.text': {}},
    {'.field.email': {}},
    {'.field.boolean': {}},
    {'.field.datetime': {}},
    {'.field.date': {}},

    {'.meta': {'*': {}}},

    {
        '.field.struct': {},
        'fields': {'.resource': {},
                   '*': {'.field.*': {}}},
    },

    {
        '.field.collection.*': {},
        'actions': {
            '.action-template.*': {},
            '*': {
                ".action": {},
                'on_collection': {'.boolean': {}},
                'method': {'.string': {}},
                'status_code': {'.integer': {}},
                'content_type': {'.string': {}},
                'read_permissions': {'.string': {}},
                'write_permissions': {'.string': {}},
                'url': {'.string': {}},
                'handler': {".handler": {}},
                'pre': {"*": {".handler": {}}},
                'post': {"*": {".handler": {}}},
            }
        },
        'fields': {'.resource': {},
                   '*': {".field.*": {}}},
        '*': {},
    },

    {
        '.apimas_app': {},
        '.meta': {},
        '*': {
            ".endpoint": {},
            ".meta": {},
            "*": {'.field.collection.*': {}},
        },
    },

    {
        '.field.collection.django': {},
        'model': {'.string': {}},
        'bound': {'.string': {}},
    },

    {
        '.action-template.django.create': {},
        'create': {
            'method': 'POST',
            'status_code': 201,
            'content_type': 'application/json',
            'on_collection': False,
            'read_permissions': 'create_response',
            'url': '/',
            'pre': {
                # '1': 'apimas.components.processors.Authentication',
                # '2': 'apimas_django.processors.UserRetrieval',
                '3': 'apimas.components.permissions.Permissions',
                '4': 'apimas.components.impexp.ImportData',
#                '5': 'apimas.components.processors.CerberusValidation',
            },
            'handler': 'apimas_django.handlers.CreateHandler',
            'post': {
                '1': 'apimas_django.processors.InstanceToDict',
                '2': 'apimas.components.impexp.ExportData'
            },
        },
    },

    {
        '.action-template.django.list': {},
        'list': {
            'method': 'GET',
            'status_code': 200,
            'content_type': 'application/json',
            'on_collection': True,
            'url': '/',
            'pre': {
    #            '1': 'apimas.components.processors.Authentication',
    #            '2': 'apimas_django.processors.UserRetrieval',
                '3': 'apimas.components.permissions.Permissions',
            },
            'handler': 'apimas_django.handlers.ListHandler',
            'post': {
                '1': 'apimas_django.processors.Filtering',
                '2': 'apimas_django.processors.InstanceToDict',
                '3': 'apimas.components.impexp.ExportData',
            }
        },
    },

    {
        '.action-template.django.retrieve': {},
        'retrieve': {
            'method': 'GET',
            'status_code': 200,
            'content_type': 'application/json',
            'on_collection': False,
            'url': '/*/',
            'pre': {
    #            '1': 'apimas.components.processors.Authentication',
    #            '2': 'apimas_django.processors.UserRetrieval',
    #            '3': 'apimas_django.processors.ObjectRetrieval',
#                '4': 'apimas_django.processors.Permissions',
            },
            'handler': 'apimas_django.handlers.RetrieveHandler',
            'post': {
                '1': 'apimas_django.processors.InstanceToDict',
                '2': 'apimas.components.impexp.ExportData',
            }
        },
    },

    {
        '.action-template.django.partial_update': {},
        'partial_update': {
            'method': 'PATCH',
            'status_code': 200,
            'content_type': 'application/json',
            'on_collection': False,
            'read_permissions': 'partial_update_response',
            'url': '/*/',
            'pre': {
    #                'apimas.components.processors.Authentication',
    #                'apimas_django.processors.UserRetrieval',
    #                'apimas_django.processors.ObjectRetrieval',
#                '4': 'apimas_django.processors.Permissions',
                '5': 'apimas.components.impexp.ImportData',
#                '6': 'apimas.components.processors.CerberusValidation',
            },
            'handler': 'apimas_django.handlers.UpdateHandler',
            'post': {
                '1': 'apimas_django.processors.InstanceToDict',
                '2': 'apimas.components.impexp.ExportData',
            },
        },
    },
]

PREDICATES = {}

for spec in spec_list:
    docular.doc_scan_spec(spec, PREDICATES)


# PREDICATES =  {
#     '.action-template.django.update': {
#         '.action-template.django.update': {},
#         'update': {
#             'method': 'PUT',
#             'url': '/',
#             'pre': [
#                 'apimas.components.processors.Authentication',
#                 'apimas_django.processors.UserRetrieval',
#                 'apimas_django.processors.ObjectRetrieval',
#                 'apimas_django.processors.Permissions',
#                 'apimas.components.processors.DeSerialization',
#                 'apimas.components.processors.CerberusValidation',
#             ],
#             'handler': 'apimas_django.handlers.UpdateHandler',
#             'post': [
#                 'apimas_django.processors.InstanceToDict',
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
#                 'apimas_django.processors.UserRetrieval',
#                 'apimas_django.processors.ObjectRetrieval',
#                 'apimas_django.processors.Permissions',
#             ],
#             'handler': 'apimas_django.handlers.DeleteHandler',
#         },
#     }
# }


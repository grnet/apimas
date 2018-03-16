import docular

spec_list = [
    {'.boolean': {}},
    {'.string': {}},
    {'.integer': {}},
    {'.float': {}},

    {'.processor.*': {},
     'module_path': {'.string': {}},
     ':*': {}},

    {'.flag.*': {}},
    {'.flag.readonly': {}},
    {'.flag.nullable': {}},
    {'.flag.filterable': {}},
    {'.flag.orderable': {}},

    {
        '.field.*': {},
        'source': {'.string': {}},
        '.flag.*': {},
        'default': {},
        '*': {},
    },

    {'.field.string': {},
     'default': {'.string': {}}},

    {'.field.serial': {},
     '.flag.readonly': {}},
    {'.field.integer': {}},
    {'.field.float': {}},

    {'.field.ref': {},
     ':root_url': {'.string': {}},
     'to': {'.string': {}}},

    {'.field.identity': {},
     ':root_url': {'.string': {}},
     'to': {'.string': {}}},

    {'.field.uuid': {}},
    {'.field.text': {}},
    {'.field.email': {}},

    {'.field.boolean': {},
     'default': {'.boolean': {}}},

    {'.field.datetime': {}},
    {'.field.date': {}},
    {'.field.file': {}},

    {'.meta': {'*': {}}},


    {
        '.field.struct': {},
        'fields': {'*': {'.field.*': {}}},
    },

    {
        '.field.collection.*': {},
        ':*': {},
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
                'handler': {".processor": {}},
                'pre': {"*": {".processor": {}}},
                'post': {"*": {".processor": {}}},
            }
        },
        'fields': {'*': {".field.*": {}}},
        '*': {},
    },

    {
        '.apimas_app': {},
        ':*': {},
        '.meta': {},
        'endpoints': {
            '*': {
                ".endpoint": {},
                ':*': {},
                ".meta": {},
                'collections': {
                    "*": {'.field.collection.*': {}},
                }
            }
        },
    },

    {
        '.field.collection.django': {},
        'model': {'.string': {}},
        'bound': {'.string': {}},
    },

    {
        '.processor.permissions': {},
        'module_path': 'apimas.components.permissions.Permissions',
        ':permission_rules': {'.string': {}},
    },

    {
        '.processor.authentication': {},
        'module_path': 'apimas.components.auth.Authentication',
        ':authenticator': {'.string': {}},
        ':verifier': {'.string': {}},
    },

    {
        '.processor.user_retrieval': {},
        'module_path': 'apimas.components.auth.UserRetrieval',
        ':user_resolver': {'.string': {}},
    },

    {
        '.processor.import_data': {},
        'module_path': 'apimas.components.impexp.ImportData',
    },

    {
        '.processor.instance_to_dict': {},
        'module_path': 'apimas_django.processors.InstanceToDict',
    },

    {
        '.processor.export_data': {},
        'module_path': 'apimas.components.impexp.ExportData',
    },

    {
        '.processor.filtering': {},
        'module_path': 'apimas_django.filtering.Filtering',
    },

    {
        '.processor.ordering': {},
        'module_path': 'apimas_django.ordering.Ordering',
    },

    {
        '.processor.object_retrieval': {},
        'module_path': 'apimas_django.processors.ObjectRetrieval',
    },

    {
        '.processor.create': {},
        'module_path': 'apimas_django.handlers.CreateHandler',
    },

    {
        '.processor.list': {},
        'module_path': 'apimas_django.handlers.ListHandler',
    },

    {
        '.processor.retrieve': {},
        'module_path': 'apimas_django.handlers.RetrieveHandler',
    },

    {
        '.processor.partial_update': {},
        'module_path': 'apimas_django.handlers.PartialUpdateHandler',
    },

    {
        '.processor.full_update': {},
        'module_path': 'apimas_django.handlers.FullUpdateHandler',
    },

    {
        '.processor.delete': {},
        'module_path': 'apimas_django.handlers.DeleteHandler',
    },

    {
        '.action-template.django.create': {},
        'create': {
            'method': 'POST',
            'status_code': 201,
            'content_type': 'application/json',
            'on_collection': False,
            'read_permissions': 'retrieve',
            'url': '/',
            'pre': {
                '1': {'.processor.authentication': {}},
                '2': {'.processor.user_retrieval': {}},
                '3': {'.processor.permissions': {}},
                '4': {'.processor.import_data': {}},
            },
            'handler': {'.processor.create': {}},
            'post': {
                '1': {'.processor.instance_to_dict': {}},
                '2': {'.processor.export_data': {}},
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
                '1': {'.processor.authentication': {}},
                '2': {'.processor.user_retrieval': {}},
                '3': {'.processor.permissions': {}},
                '4': {'.processor.import_data': {}},
            },
            'handler': {'.processor.list': {}},
            'post': {
                '1': {'.processor.filtering': {}},
                '2': {'.processor.ordering': {}},
                '3': {'.processor.instance_to_dict': {}},
                '4': {'.processor.export_data': {}},
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
                '1': {'.processor.authentication': {}},
                '2': {'.processor.user_retrieval': {}},
                '3': {'.processor.object_retrieval': {}},
                '4': {'.processor.permissions': {}},
            },
            'handler': {'.processor.retrieve': {}},
            'post': {
                '1': {'.processor.instance_to_dict': {}},
                '2': {'.processor.export_data': {}},
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
            'read_permissions': 'retrieve',
            'url': '/*/',
            'pre': {
                '1': {'.processor.authentication': {}},
                '2': {'.processor.user_retrieval': {}},
                '3': {'.processor.object_retrieval': {}},
                '4': {'.processor.permissions': {}},
                '5': {'.processor.import_data': {}},
            },
            'handler': {'.processor.partial_update': {}},
            'post': {
                '1': {'.processor.instance_to_dict': {}},
                '2': {'.processor.export_data': {}},
            },
        },
    },

    {
        '.action-template.django.update': {},
        'update': {
            'method': 'PUT',
            'status_code': 200,
            'content_type': 'application/json',
            'on_collection': False,
            'read_permissions': 'retrieve',
            'url': '/*/',
            'pre': {
                '1': {'.processor.authentication': {}},
                '2': {'.processor.user_retrieval': {}},
                '3': {'.processor.object_retrieval': {}},
                '4': {'.processor.permissions': {}},
                '5': {'.processor.import_data': {}},
            },
            'handler': {'.processor.full_update': {}},
            'post': {
                '1': {'.processor.instance_to_dict': {}},
                '2': {'.processor.export_data': {}},
            },
        },
    },

    {
        '.action-template.django.delete': {},
        'delete': {
            'method': 'DELETE',
            'status_code': 204,
            'content_type': 'application/json',
            'on_collection': False,
            'url': '/*/',
            'pre': {
                '1': {'.processor.authentication': {}},
                '2': {'.processor.user_retrieval': {}},
                '3': {'.processor.object_retrieval': {}},
                '4': {'.processor.permissions': {}},
            },
            'handler': {'.processor.delete': {}},
        },
    }
]

PREDICATES = {}

for spec in spec_list:
    docular.doc_compile_spec(spec, PREDICATES)

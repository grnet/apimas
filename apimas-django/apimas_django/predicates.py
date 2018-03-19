import docular
from apimas.predicates import PREDICATES

spec_list = [
    {
        '.field.collection.django': {},
        'model': {'.string': {}},
        'bound': {'.string': {}},
    },

    {
        '.processor.instance_to_dict': {},
        'module_path': 'apimas_django.processors.InstanceToDict',
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

for spec in spec_list:
    docular.doc_compile_spec(spec, PREDICATES)

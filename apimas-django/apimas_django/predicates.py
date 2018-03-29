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
        '.processor.search': {},
        'module_path': 'apimas_django.search.Search',
    },

    {
        '.processor.pagination': {},
        'module_path': 'apimas_django.pagination.Pagination',
        ':pagination_default_limit': {'.integer': {}},
    },

    {
        '.processor.object_retrieval_for_update': {},
        'module_path': 'apimas_django.processors.ObjectRetrievalForUpdate',
    },

    {
        '.processor.load_data.*': {},
        'module_path': 'apimas_django.loaddata.LoadData',
        ':loaddata_full': {'.boolean': {}},
    },

    {
        '.processor.load_data.partial': {},
        'module_path': 'apimas_django.loaddata.LoadData',
        ':loaddata_full': False,
    },

    {
        '.processor.response_filtering_resource.*': {},
        'module_path': 'apimas_django.permissions.FilterResourceResponse',
        ':filter_resource_strict': {'.boolean': {}},
    },

    {
        '.processor.response_filtering_resource.strict': {},
        'module_path': 'apimas_django.permissions.FilterResourceResponse',
        ':filter_resource_strict': True,
    },

    {
        '.processor.response_filtering_collection': {},
        'module_path': 'apimas_django.permissions.FilterCollectionResponse',
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
        '.processor.update': {},
        'module_path': 'apimas_django.handlers.UpdateHandler',
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
                '3': {'.processor.permissions.write': {}},
                '4': {'.processor.import_write_data': {}},
                '5': {'.processor.load_data': {}},
            },
            'handler': {'.processor.create': {}},
            'post': {
                '1': {'.processor.permissions.read.nonstrict': {}},
                '2': {'.processor.response_filtering_resource': {}},
                '3': {'.processor.instance_to_dict': {}},
                '4': {'.processor.export_data': {}},
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
                '3': {'.processor.permissions.read': {}},
                '4': {'.processor.import_params': {}},
            },
            'handler': {'.processor.list': {}},
            'post': {
                '1': {'.processor.response_filtering_collection': {}},
                '2': {'.processor.filtering': {}},
                '3': {'.processor.search': {}},
                '4': {'.processor.ordering': {}},
                '5': {'.processor.pagination': {}},
                '6': {'.processor.instance_to_dict': {}},
                '7': {'.processor.export_data': {}},
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
                '3': {'.processor.permissions.read': {}},
            },
            'handler': {'.processor.retrieve': {}},
            'post': {
                '1': {'.processor.response_filtering_resource.strict': {}},
                '2': {'.processor.instance_to_dict': {}},
                '3': {'.processor.export_data': {}},
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
                '3': {'.processor.permissions.write': {}},
                '4': {'.processor.import_write_data': {}},
                '5': {'.processor.object_retrieval_for_update': {}},
                '6': {'.processor.load_data.partial': {}},
            },
            'handler': {'.processor.update': {}},
            'post': {
                '1': {'.processor.permissions.read.nonstrict': {}},
                '2': {'.processor.response_filtering_resource': {}},
                '3': {'.processor.instance_to_dict': {}},
                '4': {'.processor.export_data': {}},
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
                '3': {'.processor.permissions.write': {}},
                '4': {'.processor.import_write_data': {}},
                '5': {'.processor.object_retrieval_for_update': {}},
                '6': {'.processor.load_data': {}},
            },
            'handler': {'.processor.update': {}},
            'post': {
                '1': {'.processor.permissions.read.nonstrict': {}},
                '2': {'.processor.response_filtering_resource': {}},
                '3': {'.processor.instance_to_dict': {}},
                '4': {'.processor.export_data': {}},
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
                '3': {'.processor.permissions.write': {}},
                '4': {'.processor.object_retrieval_for_update': {}},
            },
            'handler': {'.processor.delete': {}},
        },
    }
]

for spec in spec_list:
    docular.doc_compile_spec(spec, PREDICATES)

import docular
from apimas.predicates import PREDICATES

spec_list = [
    {
        '.field.collection.django': {},
        'model': {'.string': {}},
        'subset': {'.string': {}},
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
        'module_path': 'apimas_django.permissions.ObjectRetrievalForUpdate',
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
        '.processor.write_permission_check': {},
        'module_path': 'apimas_django.permissions.WritePermissionCheck',
    },

    {
        '.processor.read_permission_check.*': {},
        'module_path': 'apimas_django.permissions.ReadPermissionCheck',
        ':read_check_strict': {'.boolean': {}},
    },

    {
        '.processor.read_permission_check.strict': {},
        'module_path': 'apimas_django.permissions.ReadPermissionCheck',
        ':read_check_strict': True,
    },

    {
        '.processor.handler.*': {},
        ':post_handler': {'.string': {}},
    },

    {
        '.processor.handler.create': {},
        'module_path': 'apimas_django.handlers.CreateHandler',
        ':custom_create_handler': {'.string': {}},
    },

    {
        '.processor.handler.list': {},
        'module_path': 'apimas_django.handlers.ListHandler',
    },

    {
        '.processor.handler.retrieve': {},
        'module_path': 'apimas_django.handlers.RetrieveHandler',
    },

    {
        '.processor.handler.update': {},
        'module_path': 'apimas_django.handlers.UpdateHandler',
        ':custom_update_handler': {'.string': {}},
    },

    {
        '.processor.handler.delete': {},
        'module_path': 'apimas_django.handlers.DeleteHandler',
    },

    {
        '.action.django.*': {},
        'method': {'.string': {}},
        'status_code': {'.integer': {}},
        'content_type': {'.string': {}},
        'url': {'.string': {}},
        'transaction_begin_before': {'.string': {}},
        'transaction_end_after': {'.string': {}},
    },

    {
        '.action-template.django.create': {},
        'create': {
            '.action.django': {},
            'method': 'POST',
            'status_code': 201,
            'content_type': 'application/json',
            'on_collection': False,
            ':permissions_read': 'retrieve',
            'url': '/',
            'transaction_begin_before': '05',
            'transaction_end_after': '10',
            'processors': {
                '01': {'.processor.authentication': {}},
                '02': {'.processor.user_retrieval': {}},
                '03': {'.processor.permissions.write': {}},
                '04': {'.processor.import_write_data': {}},
                '05': {'.processor.load_data': {}},
                '06': {'.processor.write_permission_check': {}},
                '07': {'.processor.handler.create': {}},
                '08': {'.processor.permissions.read.nonstrict': {}},
                '09': {'.processor.response_filtering_resource': {}},
                '10': {'.processor.read_permission_check': {}},
                '11': {'.processor.instance_to_dict': {}},
                '12': {'.processor.export_data': {}},
            },
        },
    },

    {
        '.action-template.django.list': {},
        'list': {
            '.action.django': {},
            'method': 'GET',
            'status_code': 200,
            'content_type': 'application/json',
            'on_collection': True,
            'url': '/',
            'processors': {
                '01': {'.processor.authentication': {}},
                '02': {'.processor.user_retrieval': {}},
                '03': {'.processor.permissions.read': {}},
                '04': {'.processor.import_params': {}},
                '05': {'.processor.handler.list': {}},
                '06': {'.processor.response_filtering_collection': {}},
                '07': {'.processor.filtering': {}},
                '08': {'.processor.search': {}},
                '09': {'.processor.ordering': {}},
                '10': {'.processor.pagination': {}},
                '11': {'.processor.read_permission_check': {}},
                '12': {'.processor.instance_to_dict': {}},
                '13': {'.processor.export_data': {}},
            }
        },
    },

    {
        '.action-template.django.retrieve': {},
        'retrieve': {
            '.action.django': {},
            'method': 'GET',
            'status_code': 200,
            'content_type': 'application/json',
            'on_collection': False,
            'url': '/*/',
            'processors': {
                '01': {'.processor.authentication': {}},
                '02': {'.processor.user_retrieval': {}},
                '03': {'.processor.permissions.read': {}},
                '04': {'.processor.handler.retrieve': {}},
                '05': {'.processor.response_filtering_resource.strict': {}},
                '06': {'.processor.read_permission_check.strict': {}},
                '07': {'.processor.instance_to_dict': {}},
                '08': {'.processor.export_data': {}},
            }
        },
    },

    {
        '.action.django.recipe.partial_update': {},
        'content_type': 'application/json',
        'on_collection': False,
        ':permissions_read': 'retrieve',
        'transaction_begin_before': '05',
        'transaction_end_after': '11',
        'processors': {
            '01': {'.processor.authentication': {}},
            '02': {'.processor.user_retrieval': {}},
            '03': {'.processor.permissions.write': {}},
            '04': {'.processor.import_write_data': {}},
            '05': {'.processor.object_retrieval_for_update': {}},
            '06': {'.processor.load_data.partial': {}},
            '07': {'.processor.write_permission_check': {}},
            '08': {'.processor.handler.update': {}},
            '09': {'.processor.permissions.read.nonstrict': {}},
            '10': {'.processor.response_filtering_resource': {}},
            '11': {'.processor.read_permission_check': {}},
            '12': {'.processor.instance_to_dict': {}},
            '13': {'.processor.export_data': {}},
        },
    },

    {
        '.action-template.django.partial_update': {},
        'partial_update': {
            '.action.django.recipe.partial_update': {},
            'method': 'PATCH',
            'status_code': 200,
            'url': '/*/',
        },
    },

    {
        '.action-template.django.update': {},
        'update': {
            '.action.django': {},
            'method': 'PUT',
            'status_code': 200,
            'content_type': 'application/json',
            'on_collection': False,
            ':permissions_read': 'retrieve',
            'url': '/*/',
            'transaction_begin_before': '05',
            'transaction_end_after': '11',
            'processors': {
                '01': {'.processor.authentication': {}},
                '02': {'.processor.user_retrieval': {}},
                '03': {'.processor.permissions.write': {}},
                '04': {'.processor.import_write_data': {}},
                '05': {'.processor.object_retrieval_for_update': {}},
                '06': {'.processor.load_data': {}},
                '07': {'.processor.write_permission_check': {}},
                '08': {'.processor.handler.update': {}},
                '09': {'.processor.permissions.read.nonstrict': {}},
                '10': {'.processor.response_filtering_resource': {}},
                '11': {'.processor.read_permission_check': {}},
                '12': {'.processor.instance_to_dict': {}},
                '13': {'.processor.export_data': {}},
            },
        },
    },

    {
        '.action-template.django.delete': {},
        'delete': {
            '.action.django': {},
            'method': 'DELETE',
            'status_code': 204,
            'content_type': 'application/json',
            'on_collection': False,
            'url': '/*/',
            'transaction_begin_before': '04',
            'transaction_end_after': '05',
            'processors': {
                '01': {'.processor.authentication': {}},
                '02': {'.processor.user_retrieval': {}},
                '03': {'.processor.permissions.write': {}},
                '04': {'.processor.object_retrieval_for_update': {}},
                '05': {'.processor.handler.delete': {}},
            }
        },
    }
]

for spec in spec_list:
    docular.doc_compile_spec(spec, PREDICATES)

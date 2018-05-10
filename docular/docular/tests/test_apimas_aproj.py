import docular

spec_source_list = [
    {'.boolean': {}},
    {'.string': {}},
    {'.integer': {}},
    {'.float': {}},

    {'.handler': {}, '.string': {}},

    {'.flag.*': {}},
    {'.flag.readonly': {}},
    {'.flag.nullable': {}},
    {'.flag.filterable': {}},

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

    {'.field.identity': {},
     'to': {'.string': {}}},

    {'.field.uuid': {}},
    {'.field.text': {}},
    {'.field.email': {}},

    {'.field.boolean': {},
     'default': {'.boolean': {}}},

    {'.field.datetime': {}},
    {'.field.date': {}},

    {'.meta': {'*': {}}},

    {
        '.field.struct': {},
        'fields': {'*': {'.field.*': {}}},
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
        'fields': {'*': {".field.*": {}}},
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
                '3': 'apimas_django.processors.ObjectRetrieval',
                '4': 'apimas.components.permissions.Permissions',
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
                '3': 'apimas_django.processors.ObjectRetrieval',
                '4': 'apimas.components.permissions.Permissions',
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

    {
        '.action-template.django.delete': {},
        'delete': {
            'method': 'DELETE',
            'status_code': 204,
            'content_type': 'application/json',
            'on_collection': False,
            'url': '/*/',
            'pre': {
                #'1': 'apimas.components.processors.Authentication',
                #'2': 'apimas_django.processors.UserRetrieval',
                '3': 'apimas_django.processors.ObjectRetrieval',
                '4': 'apimas.components.permissions.Permissions',
            },
            'handler': 'apimas_django.handlers.DeleteHandler',
        },
    }
]


PREDICATES = {}


for spec_source in spec_source_list:
    docular.doc_compile_spec(spec_source, predicates=PREDICATES,
                             autoregister=True)


APIMAS_APP_CONFIG = {
    ".apimas_app": {},
    ".meta": {"permission_rules": "anapp.rules.get_rules"},
    "api/prefix": {
       ".endpoint": {},
        "groups": {
            ".field.collection.django": {},
            "model": "anapp.models.Group",
            "actions": {
                '.action-template.django.list': {},
                '.action-template.django.partial_update': {},
                '.action-template.django.create': {},
                '.action-template.django.retrieve': {},
                '.action-template.django.delete': {},
            },
            "fields": {
                "id": {".field.serial": {}},
                "url": {".field.identity": {},
                        '.flag.readonly': True,
                        "to": "api/prefix/groups",
                        "source": "id"},
                "name": {".field.string": {}},
                "founded": {".field.date": {}},
                "active": {".field.boolean": {},
                           'default': True},
                "email": {".field.email": {}},
                "users": {
                    '.field.collection.django': {},
                    'model': 'anapp.models.User',
                    'source': 'user_set',
                    'bound': 'group',
                    'actions': {
                        '.action-template.django.list': {},
                        '.action-template.django.create': {},
                        '.action-template.django.retrieve': {},
                        '.action-template.django.partial_update': {},
                        '.action-template.django.delete': {},
                    },
                    'fields': {
                        'id': {'.field.serial': {}},
                        'onoma': {'.field.string': {},
                                  'source': 'username'},
                        "variants": {
                            ".field.struct": {},
                            '.flag.nullable': {},
                            'default': {'=': None},
                            "source": "name_variants",
                            "fields": {
                                "en": {".field.string": {}},
                                "el": {".field.string": {}},
                            },
                        },
                        'age': {'.field.integer': {}},

                #         'emails': {
                #             '.field.collection.django': {},
                #             'model': 'anapp.models.Email',
                #             'source': 'email_set',
                #             'bound': 'user',
                #             'actions': {
                #                 '.action-template.django.list': {},
                #                 '.action-template.django.create': {},
                #                 '.action-template.django.retrieve': {},
                #             },
                #             'fields': {
                #                 'id': {'.field.serial': {}},
                #                 'email': {'.field.string': {}},
                #             }
                #         }
                    }
                }
            }
        },
    },
    # "api/prefix2": {
    #    ".endpoint": {},
    #     "groups": {
    #         ".field.collection.django": {},
    #         "model": "anapp.models.Group",
    #         "actions": {
    #             '.action-template.django.list': {},
    #             '.action-template.django.create': {},
    #             '.action-template.django.retrieve': {},
    #         },
    #         "fields": {
    #             "id": {".field.serial": {}},
    #             "url": {".field.identity": {"to": "api/prefix2/groups"},
    #                     "source": "id"},
    #             "name": {".field.string": {}},
    #         }
    #     },
    #     "users": {
    #         '.field.collection.django': {},
    #         '.field.collection.*': {},
    #         'model': 'anapp.models.User',
    #         'source': 'user_set',
    #         'bound': 'group',
    #         'actions': {
    #             '.action-template.django.list': {},
    #             '.action-template.django.create': {},
    #             '.action-template.django.retrieve': {},
    #         },
    #         'fields': {
    #             'id': {'.field.serial': {}},
    #             'username': {'.field.string': {}},
    #             'group': {'.field.ref': {"to": "api/prefix2/groups/fields"}},
    #         }
    #     },
    # },
}


DEPLOY_CONFIG = {
    ".meta": {"root_url": "http://127.0.0.1:8000/"},
}



def test_spec():
    app_spec = docular.doc_spec_config(
        {'.apimas_app': {}}, APIMAS_APP_CONFIG,
        predicates=PREDICATES)


    deployed_spec = docular.doc_spec_config(
        app_spec, DEPLOY_CONFIG,
        predicates=PREDICATES)

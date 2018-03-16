DEPLOY_CONFIG = {
    ".meta": {"root_url": "http://127.0.0.1:8000/"},
}

APP_CONFIG = {
    ".apimas_app": {},
    ".meta": {"permission_rules": "anapp.rules.get_rules"},
    'endpoints': {
        "api/prefix": {
            "posts": {
                ".field.collection.django": {},
                "auth": {
                    "authenticator": "apimas.auth.TokenAuthentication",
                    "verifier": "anapp.auth.token_verifier",
                    "user_resolver": "anapp.auth.user_resolver"
                },
                "model": "anapp.models.Post",
                "actions": {
                    '.action-template.django.list': {},
                    '.action-template.django.create': {},
                    '.action-template.django.retrieve': {},
                },
                "fields": {
                    "id": {".field.serial": {}},
                    "url": {".field.identity": {},
                            '.flag.readonly': True,
                            "to": "api/prefix/groups",
                            "source": "id"},
                    "title": {".field.string": {}},
                    "body": {".field.string": {}}
                }
            },
            "institutions": {
                ".field.collection.django": {},
                "model": "anapp.models.Institution",
                "actions": {
                    '.action-template.django.list': {},
                    '.action-template.django.retrieve': {},
                    '.action-template.django.create': {},
                    '.action-template.django.partial_update': {},
                    '.action-template.django.update': {},
                },
                "fields": {
                    "id": {".field.serial": {}},
                    "name": {".field.string": {},
                             '.flag.orderable': {}},
                    "active": {".field.boolean": {},
                               "default": True,
                               ".flag.orderable": {}},
                    "logo": {'.field.file': {},
                             '.flag.nullable': {},
                             'default': {'=': None}},
                }
            },
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
                               '.flag.filterable': {},
                               'default': True},
                    "email": {".field.email": {}},
                    "institution_id": {".field.ref": {},
                                       '.flag.filterable': {},
                                       "to": "api/prefix/institutions"},
                    "users": {
                        '.field.collection.django': {},
                        'model': 'anapp.models.User',
                        'source': 'users',
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
                                      '.flag.filterable': {},
                                      '.flag.orderable': {},
                                      'source': 'username'},
                            "variants": {
                                ".field.struct": {},
                                '.flag.nullable': {},
                                'default': {'=': None},
                                "source": "name_variants",
                                "fields": {
                                    "en": {".field.string": {},
                                           '.flag.filterable': {},
                                           '.flag.orderable': {}},
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

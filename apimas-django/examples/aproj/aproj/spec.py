DEPLOY_CONFIG = {
    ".meta": {"root_url": "http://127.0.0.1:8000/"},
}

APP_CONFIG = {
    ".apimas_app": {},
    ".meta": {"permission_rules": "anapp.rules.get_rules"},
    "api/prefix": {
       ".endpoint": {},
        "groups": {
            ".field.collection.django": {},
            "model": "anapp.models.Group",
            "actions": {
                '.action-template.django.list': {},
                '.action-template.django.create': {},
                '.action-template.django.retrieve': {},
            },
            "fields": {
                "id": {".field.serial": {}},
                "url": {".field.identity": {},
                        "to": "api/prefix/groups",
                        "source": "id"},
                "name": {".field.string": {}},
                "founded": {".field.date": {}},
                "active": {".field.boolean": {}},
                "email": {".field.email": {}},
                "users": {
                    '.field.collection.django': {},
                    '.field.collection.*': {},
                    'model': 'anapp.models.User',
                    'source': 'user_set',
                    'bound': 'group',
                    # 'actions': {
                    #     '.action-template.django.list': {},
                    #     '.action-template.django.create': {},
                    #     '.action-template.django.retrieve': {},
                    # },
                    'fields': {
                        'id': {'.field.serial': {}},
                        'username': {'.field.string': {}},
                        "name_variants": {
                            ".field.struct": {},
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

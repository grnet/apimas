CONFIG = {
    ".apimas_app": {},
    ".meta": {"get_rules": "anapp.rules.get_rules"},
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
                ".resource": {},
                "id": {".field.serial": {}},
                "url": {".field.identity": {"to": "api/prefix/groups"},
                        "source": "id"},
                "name": {".field.string": {}},
                "users": {
                    '.field.collection.django': {},
                    '.field.collection.*': {},
                    'model': 'anapp.models.User',
                    'source': 'user_set',
                    'bound': 'group',
                    'actions': {
                        '.action-template.django.list': {},
                        '.action-template.django.create': {},
                        '.action-template.django.retrieve': {},
                    },
                    'fields': {
                        'id': {'.field.serial': {}},
                        'username': {'.field.string': {}},
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
    #             ".resource": {},
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
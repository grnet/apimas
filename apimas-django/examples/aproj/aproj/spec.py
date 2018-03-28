import copy

DEPLOY_CONFIG = {
    ":root_url": "http://127.0.0.1:8000/",
}

POSTS = {
    ".field.collection.django": {},

    ':permissions_namespace': 'anapp.models',
    ":authenticator": "apimas.auth.TokenAuthentication",
    ":verifier": "anapp.auth.token_verifier",
    ":user_resolver": "anapp.auth.user_resolver",
    ":pagination_default_limit": 5,

    "model": "anapp.models.Post",
    "actions": {
        '.action-template.django.list': {},
        '.action-template.django.create': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.partial_update': {},
    },
    "fields": {
        "id": {".field.serial": {}},
        "url": {".field.identity": {},
                '.flag.readonly': {},
                "to": "api/prefix/groups",
                "source": "id"},
        "title": {".field.string": {}},
        "body": {".field.string": {}},
        "status": {".field.string": {},
                   "default": "posted"},
    }
}

POSTS2 = copy.deepcopy(POSTS)
POSTS2[':permissions_namespace'] = 'anapp'

NULLTEST = {
    '.field.collection.django': {},
    'model': 'anapp.models.Nulltest',
    "actions": {
        '.action-template.django.list': {},
        '.action-template.django.create': {},
        '.action-template.django.retrieve': {},
    },
    'fields': {
        "id": {".field.serial": {}},
        'fdef': {'.field.integer': {},
                 '.flag.nullable.default': {}},
        'fnodef': {'.field.integer': {},
                   '.flag.nullable': {}},
    },
}

INSTITUTIONS = {
    ".field.collection.django": {},
    "model": "anapp.models.Institution",
    "actions": {
        '.action-template.django.list': {},
        '.action-template.django.retrieve': {},
        '.action-template.django.create': {},
        '.action-template.django.partial_update': {},
        '.action-template.django.update': {},
        '.action-template.django.delete': {},
    },
    "fields": {
        "id": {".field.serial": {}},
        "name": {".field.string": {},
                 '.flag.orderable': {}},
        "active": {".field.boolean": {},
                   "default": True,
                   ".flag.orderable": {}},
        "category": {".field.choices": {},
                     "allowed": {
                         '=': ["Institution", "Research"]},
                     "displayed": {
                     '=': ["Institution", "Research Center"]},
                     "default": "Research"},
        "category_raw": {
            ".field.choices": {},
            ".flag.readonly": {},
            "source": "category",
            "allowed": {
                '=': ["Institution", "Research"]},
        },
        "logo": {'.field.file': {},
                 'default': ''},
    }
}

GROUPS = {
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
        "id": {".field.uuid": {},
               '.flag.readonly': {}},
        "url": {".field.identity": {},
                '.flag.readonly': {},
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
        'institution': {
            '.field.struct': {},
            '.flag.readonly': {},
            'fields': INSTITUTIONS['fields']},
        "users": {
            '.field.collection.django': {},
            ':filter_compat': True,
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
                          '.flag.searchable': {},
                          '.flag.orderable': {},
                          'source': 'username'},
                "variants": {
                    ".field.struct": {},
                    '.flag.nullable': {},
                    'default': {'=': None},
                    "source": "name_variants",
                    "fields": {
                        "en": {".field.string": {},
                               '.flag.searchable': {},
                               '.flag.filterable': {},
                               '.flag.orderable': {}},
                        "el": {".field.string": {},
                               '.flag.searchable': {}},
                    },
                },
                'age': {'.field.integer': {},
                        '.flag.filterable': {}},
            }
        }
    }
}

FEATURES = {
    ".field.collection.django": {},
    "model": "anapp.models.Feature",
    "actions": {
        '.action-template.django.retrieve': {},
        '.action-template.django.create': {},
    },
    "fields": {
        "id": {".field.serial": {}},
        "name": {".field.string": {},
                 '.flag.orderable': {}},
        "group_id": {'.field.ref': {},
                     'to': 'api/prefix/groups'}
    }
}

APP_CONFIG = {
    ".apimas_app": {},
    ":permission_rules": "anapp.rules.get_rules",
    'endpoints': {
        "api/prefix": {
            "collections": {
                "posts": POSTS,
                "posts2": POSTS2,
                'nulltest': NULLTEST,
                "institutions": INSTITUTIONS,
                "groups": GROUPS,
                "features": FEATURES,
            },
        },
    },
}

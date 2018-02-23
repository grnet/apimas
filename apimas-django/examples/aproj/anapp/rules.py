# COLUMNS = ('collection', 'action', 'role', 'field', 'state', 'comment')

RULES = [


    ('api/prefix/groups', 'list', '*', '*', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users/username', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users/name_variants/el', '*', '*'),
#    ('api/prefix/groups', 'list', '*', 'users/name_variants', '*', '*'),

    ('api/prefix/groups', 'create', '*', 'users/name_variants', '*', '*'),
    ('api/prefix/groups', 'create', '*', 'users', '*', '*'),
    ('api/prefix/groups', 'create', '*', 'name', '*', '*'),

    ('api/prefix/groups', 'create', '*', '*', '*', '*'),

    ('api/prefix/groups', 'retrieve', '*', '*', '*', '*'),

    ('api/prefix/groups', 'create_response', '*', 'id', '*', '*'),
    ('api/prefix/groups', 'create_response', '*', 'url', '*', '*'),
    ('api/prefix/groups', 'create_response', '*', 'users/username', '*', '*'),
    ('api/prefix/groups', 'create_response', '*', 'users/age', '*', '*'),

    ('api/prefix/groups/users', 'list', '*', 'users', '*', '*'),
    ('*', 'retrieve', '*', 'url', '*', '*'),
    ('*', 'retrieve', '*', 'name', '*', '*'),
    ('*', 'create', '*', '*', '*', '*'),
]

def get_rules():
    return RULES


def get_rules2():
    return RULES

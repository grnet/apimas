# COLUMNS = ('collection', 'action', 'role', 'filter', 'check' 'fields', 'comment')

RULES = [

    ('api/prefix/institutions', 'retrieve', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'list', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'partial_update', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'update', '*', '*', '*', '*', '*'),
    ('api/prefix/institutions', 'delete', '*', '*', '*', '*', '*'),

    ('api/prefix/groups', 'list', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'retrieve', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'partial_update', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/groups', 'delete', '*', '*', '*', '*', '*'),

    ('api/prefix/groups/users', 'list', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'retrieve', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'partial_update', '*', '*', '*', '*', '*'),
    ('api/prefix/groups/users', 'delete', '*', '*', '*', '*', '*'),

    ('api/prefix/posts', 'list', '*', '*', '*', '*', '*'),
    ('api/prefix/posts', 'create', 'admin', '*', '*', '*', '*'),
    ('api/prefix/posts', 'retrieve', 'admin', 'is_posted', '*', '*', '*'),
    ('api/prefix/posts', 'retrieve', 'user', 'is_posted', '*', 'id,title,status', '*'),

    ('api/prefix/posts2', 'retrieve', 'user', 'Post.is_posted', '*', '*', '*'),

    ('api/prefix/nulltest', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/nulltest', 'retrieve', '*', '*', '*', '*', '*'),

    ('api/prefix/features', 'create', '*', '*', '*', '*', '*'),
    ('api/prefix/features', 'retrieve', '*', '*', '*', '*', '*'),
]

def get_rules():
    return RULES


def get_rules2():
    return RULES

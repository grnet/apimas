# COLUMNS = ('collection', 'action', 'role', 'field', 'state', 'comment')

RULES = [
    ('api/prefix/groups', 'list', '*', 'url', '*', '*'),
    ('api/prefix/groups', 'list', '*', 'users', '*', '*'),
    ('api/prefix/groups/users', 'list', '*', 'users', '*', '*'),
    ('*', 'retrieve', '*', 'url', '*', '*'),
    ('*', 'retrieve', '*', 'name', '*', '*'),
    ('*', 'create', '*', '*', '*', '*'),
]

def get_rules():
    return RULES


def get_rules2():
    return RULES

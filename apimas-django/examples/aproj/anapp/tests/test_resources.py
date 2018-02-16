from apimas_django.test import *


def test_groups(client):
    """
    Groups resource tests
    """
    api = client.copy(prefix='/api/prefix/')
    assert api.get('groups').json() == []

    group1 = api.post('groups', {'name': 'users'}).json()
    assert group1.get('name') == 'users'
    assert group1.get('id') == 1
    group2 = api.post('groups', {'name': 'users'}).json()

    # groups created
    assert len(api.get('groups').json()) == 2

    # method not allowed
    assert api.delete('groups/1').status_code == 405

from apimas_django.test import *

pytestmark = pytest.mark.django_db(transaction=False)


def test_posts(client):
    api = client.copy(prefix='/api/prefix/')
    admin = client.copy(prefix='/api/prefix', auth_token='admin-admin-1234')
    assert api.get('posts').json() == []

    post = dict(title="Post title", body="Post content")
    resp = api.post('posts', post)
    assert resp.status_code == 403

    resp = admin.post('posts', post)
    assert resp.status_code == 201


def test_groups(client):
    """
    Groups resource tests
    """
    api = client.copy(prefix='/api/prefix/')
    assert api.get('groups').json() == []

    resp = api.post('groups', {
        'name': 'users',
        'founded': '2014-12-31',
        'active': True
    })
    assert resp.status_code == 400
    assert "'email': Field is required" in resp.json().get("details")

    resp = api.post('groups', {
        'name': 'users',
        'founded': '2014-12-31',
        'active': True,
        'email': 'users@apim.as'
    })
    assert resp.status_code == 201

    group1 = resp.json()
    # test create_response permissions
    assert u'name' in group1
    assert u'founded' in group1
    assert u'active' in group1

    resp = api.post('groups', {
        'name': 'users',
        'founded': '2014-12-31',
        'email': 'group@api.mas',
        'active': True
    })
    assert resp.status_code == 201

    assert group1.get('url').endswith('groups/{}/'.format(group1.get('id')))
    group1 = api.get(group1.get('url'))
    assert group1.status_code == 200

    # groups created
    resp = api.get('groups')
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # method not allowed
    assert api.delete('groups/1').status_code == 405

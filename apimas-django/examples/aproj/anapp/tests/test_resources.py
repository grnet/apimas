from django.core.files.uploadedfile import SimpleUploadedFile
from apimas_django.test import *
from anapp import models
from datetime import datetime

pytestmark = pytest.mark.django_db(transaction=False)


def test_posts(client):
    api = client.copy(prefix='/api/prefix/')
    admin = client.copy(prefix='/api/prefix', auth_token='admin-admin-1234')
    user = client.copy(prefix='/api/prefix', auth_token='user-user-1234')
    assert api.get('posts').json() == []

    post = dict(title="Post title", body="Post content")
    resp = api.post('posts', post)
    assert resp.status_code == 403
    assert not resp.has_header('WWW-Authenticate')

    resp = user.post('posts', post)
    assert resp.status_code == 401
    assert resp.has_header('WWW-Authenticate')

    resp = admin.post('posts', post)
    assert resp.status_code == 201


def test_groups(client):
    """
    Groups resource tests
    """
    api = client.copy(prefix='/api/prefix/')
    assert api.get('groups').json() == []

    resp = api.post('institutions', dict(name="inst1"))
    assert resp.status_code == 201
    inst = resp.json()
    inst_id = inst['id']

    resp = api.get('institutions/%s' % inst_id)
    assert resp.status_code == 200
    retr_inst = resp.json()
    assert inst == retr_inst

    group_data = {
        'name': 'users',
        'founded': '2014-12-31',
        'active': True,
        'institution_id': inst.get('id')
    }
    resp = api.post('groups', group_data)
    assert resp.status_code == 400
    assert "'email': Field is required" in resp.json().get("details")

    group_data['email'] = 'group@apim.as'
    resp = api.post('groups', group_data)
    assert resp.status_code == 201

    group1 = resp.json()
    # test create_response permissions
    assert u'name' in group1
    assert u'founded' in group1
    assert u'active' in group1

    resp = api.post('groups', group_data)
    assert resp.status_code == 201

    assert group1.get('url').endswith('groups/{}/'.format(group1.get('id')))
    resp = api.get(group1.get('url'))
    assert resp.status_code == 200

    # groups created
    resp = api.get('groups')
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # method not allowed
    assert api.delete('groups/{}'.format(group1.get('id'))).status_code == 204


def filter_dict(keys):
    def f(d):
        return {k: v for k, v in d.iteritems() if k in keys}
    return f


def test_orderable(client):
    api = client.copy(prefix='/api/prefix/')
    insts = [
        {'name': 'bbb', 'active': True},
        {'name': 'aaa', 'active': True},
        {'name': 'ccc', 'active': False},
    ]
    for inst in insts:
        models.Institution.objects.create(**inst)

    resp = api.get('institutions', {'ordering': 'active,-name'})
    body = resp.json()
    cleaned = map(filter_dict(['name', 'active']), body)
    assert cleaned[0] == insts[2]
    assert cleaned[1] == insts[0]
    assert cleaned[2] == insts[1]


def test_filter(client):
    api = client.copy(prefix='/api/prefix/')
    inst = models.Institution.objects.create(name='inst1', active=True)
    gr = models.Group.objects.create(
        name='gr1', founded=datetime.now(), active=True,
        email='group1@example.com', institution=inst)

    gr2 = models.Group.objects.create(
        name='gr2', founded=datetime.now(), active=False,
        email='group2@example.com', institution=inst)

    data = {'onoma': 'Georgios', 'age': 22,
            'variants': {'en': 'George', 'el': 'Giorgos'}}
    resp = api.post('groups/%s/users' % gr.id, data)
    assert resp.status_code == 201

    data = {'onoma': 'Georgia', 'age': 22,
            'variants': {'en': 'Georgia', 'el': 'Giorgia'}}
    resp = api.post('groups/%s/users' % gr.id, data)
    assert resp.status_code == 201

    data = {'onoma': 'Konstantinos', 'age': 33,
            'variants': {'en': 'Constantine', 'el': 'Kostas'}}
    resp = api.post('groups/%s/users' % gr.id, data)
    assert resp.status_code == 201

    resp = api.get('groups', {'institution_id': 1})
    assert resp.status_code == 400
    assert 'Unrecognized parameter' in resp.json()['details']

    resp = api.get('groups', {'flt__institution_id': 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = api.get('groups', {'flt__active': True, 'flt__institution_id': 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get('groups', {'flt__active': True, 'flt__institution_id': 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = api.get('groups', {'flt__users.onoma': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = api.get('groups', {'flt__users.onoma__startswith': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Using filter_compat = True
    users_path = 'groups/%s/users' % gr.id

    resp = api.get(users_path, {'flt__onoma': 'Georg'})
    assert resp.status_code == 403

    resp = api.get(users_path, {'onoma': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = api.get(users_path, {'onoma': 'Georgios'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get(users_path, {'age': 22, 'variants__en': 'George'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get(users_path, {'age': 22})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = api.get(users_path)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_search(client):
    api = client.copy(prefix='/api/prefix/')
    inst = models.Institution.objects.create(name='inst1', active=True)
    gr = models.Group.objects.create(
        name='gr1', founded=datetime.now(), active=True,
        email='group1@example.com', institution=inst)

    data = {'onoma': 'Georgios', 'age': 22,
            'variants': {'en': 'George', 'el': 'Giorgos'}}
    resp = api.post('groups/%s/users' % gr.id, data)
    assert resp.status_code == 201

    data = {'onoma': 'Georgia', 'age': 22,
            'variants': {'en': 'Georgia', 'el': 'Giorgia'}}
    resp = api.post('groups/%s/users' % gr.id, data)
    assert resp.status_code == 201

    resp = api.get('groups/%s/users' % gr.id, {'search': 'nonex'})
    assert resp.status_code == 200
    assert resp.json() == []

    resp = api.get('groups/%s/users' % gr.id, {'search': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = api.get('groups/%s/users' % gr.id, {'search': 'Georgios'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get('groups/%s/users' % gr.id, {'search': 'Giorgos'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get('groups', {'search': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_subelements(client):
    api = client.copy(prefix='/api/prefix/')
    inst_obj = models.Institution.objects.create(name='inst', active=True)
    inst_id = inst_obj.id

    resp = api.get('institutions/%s' % inst_id)
    assert resp.status_code == 200
    inst = resp.json()

    data = {
        'name': 'users',
        'founded': '2014-12-31',
        'active': True,
        'institution_id': inst_id,
        'institution': {'name': 'one'},
        'email': 'email@example.com',
        'users': [{'onoma': 'Georgios', 'age': 22,
                   'variants': {'el': 'Giorgos', 'en': 'George'}}],
    }
    resp = api.post('groups', data)
    assert resp.status_code == 400
    assert 'readonly' in resp.json()['details']

    data.pop('institution')
    resp = api.post('groups', data)
    assert resp.status_code == 201
    body = resp.json()
    group_id = body['id']
    assert body['institution'] == inst
    users = body['users']
    assert len(users) == 1
    assert users[0]['onoma'] == 'Georgios'
    user_id = users[0]['id']

    data = {
        'email': 'other@example.com',
        'users': [{'onoma': 'Georgios', 'age': 22,
                   'variants': {'el': 'Giorgos', 'en': 'George'}}],
    }

    group_path = 'groups/%s' % group_id
    resp = api.patch(group_path, data)
    assert resp.status_code == 200
    body = resp.json()
    assert body['email'] == 'other@example.com'
    users = body['users']
    assert len(users) == 1
    assert users[0]['onoma'] == 'Georgios'
    new_user_id = users[0]['id']
    assert new_user_id > user_id
    assert not models.User.objects.filter(id=user_id).exists()

    name_variants_id = models.User.objects.get(id=new_user_id).name_variants_id
    user_path = group_path + '/users/%s' % new_user_id
    data = {'onoma': 'Georgia', 'variants': {'el': 'Giorgia', 'en': 'Georgia'}}
    resp = api.patch(user_path, data)
    assert resp.status_code == 200
    body = resp.json()
    assert body['variants']['el'] == 'Giorgia'
    new_name_variants_id = models.User.objects.get(
        id=new_user_id).name_variants_id

    assert name_variants_id == new_name_variants_id


def test_update(client):
    api = client.copy(prefix='/api/prefix/')
    models.Institution.objects.create(name='aaa', active=True)

    data = {'active': False}
    resp = api.put('institutions/1', data)
    assert resp.status_code == 400
    assert 'Field is required' in resp.content  # 'name' is required

    resp = api.patch('institutions/1', data)
    assert resp.status_code == 200
    inst = resp.json()
    assert inst['active'] == False

    data = {'name': 'bbb'}
    resp = api.put('institutions/1', data)
    assert resp.status_code == 200
    inst = resp.json()
    assert inst['name'] == 'bbb'
    assert inst['active'] == True  # default value


def test_delete(client):
    api = client.copy(prefix='/api/prefix/')
    inst1 = models.Institution.objects.create(name='inst1', active=True)
    inst2 = models.Institution.objects.create(name='inst2', active=True)
    gr = models.Group.objects.create(
        name='gr1', founded=datetime.now(), active=True,
        email='group1@example.com', institution=inst2)

    resp = api.get('institutions')
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = api.delete('institutions/%s/' % inst1.id)
    assert resp.status_code == 204

    resp = api.delete('institutions/%s/' % inst2.id)
    assert resp.status_code == 403

    resp = api.get('institutions')
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_choices(client):
    api = client.copy(prefix='/api/prefix/')

    data = {'name': 'inst1', 'category': 'other'}
    resp = api.post('institutions', data)
    assert resp.status_code == 400

    data = {'name': 'inst1', 'category': 'Research'}
    resp = api.post('institutions', data)
    assert resp.status_code == 400

    data = {'name': 'inst1', 'category': 'Research Center'}
    resp = api.post('institutions', data)
    assert resp.status_code == 201
    inst = resp.json()
    inst_id = inst['id']
    assert inst['category'] == 'Research Center'
    assert inst['category_raw'] == 'Research'

    inst1 = models.Institution.objects.get(id=inst_id)
    assert inst1.category == 'Research'


def test_files(client):
    api = client.copy(prefix='/api/prefix/')
    models.Institution.objects.create(name='aaa', active=True)

    resp = api.get('institutions/1')
    assert resp.status_code == 200
    assert resp.json()['logo'] == ''

    logo = SimpleUploadedFile('logo1.png', 'logodata')
    resp = api.patch('institutions/1',
                   {'name': 'bbb', 'logo': logo},
                   content_type=MULTIPART_CONTENT)

    assert resp.status_code == 200
    assert resp.json()['logo'].startswith('logos/logo1')


def test_nullable(client):
    api = client.copy(prefix='/api/prefix/')
    data = {}
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert 'fnodef' in resp.json()['details']

    data = {'fdef': 4}
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert 'fnodef' in resp.json()['details']

    data = {'fnodef': 4}
    resp = api.post('nulltest', data)
    assert resp.status_code == 201
    body = resp.json()
    assert body['fdef'] is None
    assert body['fnodef'] == 4

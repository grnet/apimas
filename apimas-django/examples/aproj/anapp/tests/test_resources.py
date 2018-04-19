# -*- coding: utf-8 -*-

from django.core.files.uploadedfile import SimpleUploadedFile
from apimas_django.test import *
from anapp import models
from datetime import datetime
import uuid
import unicodedata

pytestmark = pytest.mark.django_db(transaction=False)


def is_uuid(value):
    try:
        uuid.UUID(value)
        return True
    except:
        return False


def test_users(client):
    api = client.copy(prefix='/api/prefix/')
    username = unicodedata.normalize('NFD', u'Jörg')
    data = {
        'feature': 'feature',
        'user': {
            'username': username,
            'password': 'pass',
            'first_name': 'first',
            'last_name': 'last',
            'email': 'uname@example.org',
            'role': 'user',
            'token': 'usertoken',
        }
    }
    r = api.post('enhanceduser', data)
    assert r.status_code == 201
    body = r.json()
    assert len(body) == 1
    enhanceduser_id = body['id']

    e_user = models.EnhancedUser.objects.get(id=enhanceduser_id)
    assert e_user.user.username != username
    assert e_user.user.username == unicodedata.normalize('NFKC', username)
    first_password = e_user.user.password
    assert first_password.startswith('pbkdf2')

    user = client.copy(prefix='/api/prefix', auth_token='usertoken')
    r = user.get('enhanceduser/%s' % enhanceduser_id)
    assert r.status_code == 200
    body = r.json()
    assert body['user']['username'] == unicodedata.normalize('NFKC', username)
    user_id = body['user']['id']

    # other users fails to retrieve
    models.User.objects.create_user(
        'xristis', role='user', token='XRISTISTOKEN')
    xristis = client.copy(prefix='/api/prefix', auth_token='XRISTISTOKEN')
    r = xristis.get('enhanceduser/%s' % enhanceduser_id)
    assert r.status_code == 404

    data = {
        'user': {
            'first_name': 'First',
            'last_name': 'Last',
            'password': 'newpass',
        }
    }
    r = user.patch('enhanceduser/%s' % enhanceduser_id, data)
    assert r.status_code == 200

    e_user = models.EnhancedUser.objects.get(id=enhanceduser_id)
    assert e_user.user_id == user_id
    assert e_user.user.first_name == 'First'
    assert e_user.user.password != first_password
    assert e_user.user.password.startswith('pbkdf2')


def test_permissions(client):
    models.User.objects.create_user('admin', role='admin', token='ADMINTOKEN')
    models.User.objects.create_user('user', role='user', token='USERTOKEN')
    models.User.objects.create_user(
        'xristis', role='user', token='XRISTISTOKEN')

    api = client.copy(prefix='/api/prefix/')
    admin = client.copy(prefix='/api/prefix', auth_token='ADMINTOKEN')
    user = client.copy(prefix='/api/prefix', auth_token='USERTOKEN')
    xristis = client.copy(prefix='/api/prefix', auth_token='XRISTISTOKEN')

    # anonymous can't list
    resp = api.get('posts')
    assert resp.status_code == 403

    resp = admin.get('posts')
    assert resp.status_code == 200
    assert resp.json() == []

    post = dict(title="Post title", body="Post content")

    # anonymous can't create
    resp = api.post('posts', post)
    assert resp.status_code == 403
    assert not resp.has_header('WWW-Authenticate')

    assert not models.PostLog.objects.all().exists()

    # user creates pending post
    resp = user.post('posts', post)
    assert resp.status_code == 201
    body = resp.json()
    post_pending_id = body['id']
    assert body['status'] == 'pending'
    assert set(body.keys()) == set(['id', 'url', 'title', 'body', 'status'])

    assert models.PostLog.objects.filter(
        post_id=post_pending_id,
        username='user',
        action='create').exists()

    # user can't create a posted post
    post['status'] = 'posted'
    resp = user.post('posts', post)
    assert resp.status_code == 400

    # user can create a hidden post but cannot view it
    post['status'] = 'hidden'
    resp = user.post('posts', post)
    assert resp.status_code == 201
    body = resp.json()
    assert body is None
    post_hidden_id = post_pending_id + 1

    # admin can create and view a posted post
    post['status'] = 'posted'
    post['body'] = 'Post xristis content'
    resp = admin.post('posts', post)
    assert resp.status_code == 201
    body = resp.json()
    assert body['status'] == 'posted'
    post_posted_id = body['id']
    assert post_posted_id > post_hidden_id

    # admin can retrieve the hidden post
    resp = admin.get('posts/%s' % post_hidden_id)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'hidden'

    # admin lists every post
    resp = admin.get('posts')
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    # user list all but hidden posts
    resp = user.get('posts')
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert all(map(lambda s: s != 'hidden',
                   (elem['status'] for elem in body)))

    ### Updates
    # user can update the pending post
    resp = user.patch('posts/%s' % post_pending_id, {'title': 'another title'})
    assert resp.status_code == 200

    # user can't update the posted post
    resp = user.patch('posts/%s' % post_posted_id, {'title': 'another title'})
    assert resp.status_code == 404

    # admin can update the posted post
    resp = admin.patch('posts/%s' % post_posted_id, {'title': 'another title'})
    assert resp.status_code == 200

    # user views all fields of the post
    resp = user.get('posts/%s' % post_posted_id)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == set(['id', 'url', 'title', 'body', 'status'])

    # anonymous can't view a pending post
    resp = api.get('posts/%s' % post_pending_id)
    assert resp.status_code == 404

    # anonymous views a field subset of a posted post
    resp = api.get('posts/%s' % post_posted_id)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == set(['id', 'title', 'status'])

    # user can't delete any post
    resp = user.delete('posts/%s' % post_hidden_id)
    assert resp.status_code == 403

    # admin can't delete a posted post
    resp = admin.delete('posts/%s' % post_posted_id)
    assert resp.status_code == 404

    assert not models.PostLog.objects.filter(action='delete').exists()

    # admin can delete a hidden post
    resp = admin.delete('posts/%s' % post_hidden_id)
    assert resp.status_code == 204

    assert models.PostLog.objects.filter(
        post_id=post_hidden_id,
        username='admin',
        action='delete').exists()

    # post is deleted
    resp = admin.get('posts/%s' % post_hidden_id)
    assert resp.status_code == 404

    # posts2: all users view posted posts, all fields
    resp = api.get('posts2/%s' % post_pending_id)
    assert resp.status_code == 404

    resp = admin.get('posts2/%s' % post_pending_id)
    assert resp.status_code == 404

    resp = api.get('posts2/%s' % post_posted_id)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == set(['id', 'url', 'title', 'body', 'status'])
    assert body['status'] == 'posted'

    ### Write checks
    # user can't change state to hidden
    resp = user.patch('posts/%s' % post_pending_id, {'title': 'new title',
                                                     'status': 'hidden'})
    assert resp.status_code == 400

    # user can change state to posted
    resp = user.patch('posts/%s' % post_pending_id, {'title': 'new title',
                                                     'status': 'posted'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'posted'
    post_nowposted_id = post_pending_id

    # user can't change body field
    resp = user.patch('posts/%s' % post_pending_id, {'body': 'new body'})
    assert resp.status_code == 403

    # admin can change state to hidden
    resp = admin.patch('posts/%s' % post_nowposted_id, {'status': 'hidden'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'hidden'

    # and back to posted
    resp = admin.patch('posts/%s' % post_nowposted_id, {'status': 'posted'})
    assert resp.status_code == 200
    assert resp.json()['status'] == 'posted'

    ### Read checks
    resp = xristis.get('posts')
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]['id'] == post_nowposted_id

    # This particular user can't see this post
    resp = xristis.get('posts/%s' % post_posted_id)
    assert resp.status_code == 404

    resp = user.get('posts/%s' % post_posted_id)
    assert resp.status_code == 200

    # This particular user can create this post but cannot view it
    post = {'title': 'title', 'body': 'xristis mentioned'}
    resp = xristis.post('posts', post)
    assert resp.status_code == 201
    body = resp.json()
    assert body is None

    # The other user can create and view it too
    post = {'title': 'title', 'body': 'xristis mentioned'}
    resp = user.post('posts', post)
    assert resp.status_code == 201
    body = resp.json()
    assert body['body'] == 'xristis mentioned'


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

    resp = api.get('institutions', {'ordering': 'category'})
    assert resp.status_code == 403
    assert "not orderable" in resp.content

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
    resp = api.post('groups/%s/members' % gr.id, data)
    assert resp.status_code == 201

    data = {'onoma': 'Georgia', 'age': 22,
            'variants': {'en': 'Georgia', 'el': 'Giorgia'}}
    resp = api.post('groups/%s/members' % gr.id, data)
    assert resp.status_code == 201

    data = {'onoma': 'Konstantinos', 'age': 33,
            'variants': {'en': 'Constantine', 'el': 'Kostas'}}
    resp = api.post('groups/%s/members' % gr.id, data)
    assert resp.status_code == 201

    resp = api.get('groups', {'institution_id': 1})
    assert resp.status_code == 400
    assert 'Unrecognized parameter' in resp.json()['details']

    resp = api.get('groups', {'flt__name': 'members'})
    assert resp.status_code == 403
    assert "not filterable" in resp.content

    resp = api.get('groups', {'flt__institution_id': 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = api.get('groups', {'flt__active': True, 'flt__institution_id': 1})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get('groups', {'flt__active': True, 'flt__institution_id': 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = api.get('groups', {'flt__members.onoma': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = api.get('groups', {'flt__members.onoma__illegal': 'Georg'})
    assert resp.status_code == 403
    assert "No such operator" in resp.content

    resp = api.get('groups', {'flt__members.onoma__startswith': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Using filter_compat = True
    members_path = 'groups/%s/members' % gr.id

    resp = api.get(members_path, {'flt__onoma': 'Georg'})
    assert resp.status_code == 403

    resp = api.get(members_path, {'onoma': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = api.get(members_path, {'onoma': 'Georgios'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get(members_path, {'age': 22, 'variants__en': 'George'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get(members_path, {'age': 22})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = api.get(members_path)
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
    resp = api.post('groups/%s/members' % gr.id, data)
    assert resp.status_code == 201

    data = {'onoma': 'Georgia', 'age': 22,
            'variants': {'en': 'Georgia', 'el': 'Giorgia'}}
    resp = api.post('groups/%s/members' % gr.id, data)
    assert resp.status_code == 201

    resp = api.get('groups/%s/members' % gr.id, {'search': 'nonex'})
    assert resp.status_code == 200
    assert resp.json() == []

    resp = api.get('groups/%s/members' % gr.id, {'search': 'Georg'})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = api.get('groups/%s/members' % gr.id, {'search': 'Georgios'})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = api.get('groups/%s/members' % gr.id, {'search': 'Giorgos'})
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
        'members': [{'onoma': 'Georgios', 'age': 22,
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
    members = body['members']
    assert len(members) == 1
    assert members[0]['onoma'] == 'Georgios'
    user_id = members[0]['id']

    data = {
        'email': 'other@example.com',
        'members': [{'onoma': 'Georgios', 'age': 22,
                     'variants': {'el': 'Giorgos', 'en': 'George'}}],
    }

    group_path = 'groups/%s' % group_id
    resp = api.patch(group_path, data)
    assert resp.status_code == 200
    body = resp.json()
    assert body['email'] == 'other@example.com'
    members = body['members']
    assert len(members) == 1
    assert members[0]['onoma'] == 'Georgios'
    new_user_id = members[0]['id']
    assert new_user_id > user_id
    assert not models.Member.objects.filter(id=user_id).exists()

    name_variants_id = models.Member.objects.get(
        id=new_user_id).name_variants_id
    user_path = group_path + '/members/%s' % new_user_id
    data = {'onoma': 'Georgia', 'variants': {'el': 'Giorgia', 'en': 'Georgia'}}
    resp = api.patch(user_path, data)
    assert resp.status_code == 200
    body = resp.json()
    assert body['variants']['el'] == 'Giorgia'
    new_name_variants_id = models.Member.objects.get(
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


def test_ref(client):
    api = client.copy(prefix='/api/prefix/')

    data = {'name': 'inst1', 'category': 'Research Center'}
    resp = api.post('institutions', data)
    assert resp.status_code == 201
    inst = resp.json()
    inst_id = inst['id']
    assert isinstance(inst_id, int)

    data = {
        'name': 'group1',
        'founded': '2014-12-31',
        'active': True,
        'institution_id': inst_id,
        'email': 'group1@example.com',
    }
    resp = api.post('groups', data)
    assert resp.status_code == 201
    group = resp.json()
    group_id = group['id']
    assert is_uuid(group_id)
    group_url = group['url']

    data = {'name': 'name', 'group_id': group_id}
    resp = api.post('features', data)
    assert resp.status_code == 201
    body = resp.json()
    assert body['group_id'] == group_url

    data = {'name': 'another', 'group_id': group_url}
    resp = api.post('features', data)
    assert resp.status_code == 201
    body = resp.json()
    assert body['group_id'] == group_url
    assert body['group_name'] == 'group1'
    assert body['institution_name'] == 'inst1'


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


def test_importing(client):
    api = client.copy(prefix='/api/prefix/')

    data = {'fnodef': None}
    resp = api.post('nulltest', data)
    assert resp.status_code == 201
    body = resp.json()
    assert body['fnodef'] is None
    assert body['fstr'] == 'other'

    data = {'fnodef': None, 'fstr': None}
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert "cannot be None" in resp.content

    data = {'fnodef': None, 'fstr': 17}
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert "is not of type 'string'" in resp.content

    data = {'fnodef': None, 'fbool': 17}
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert "is not boolean" in resp.content

    data = {'fnodef': 'other'}
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert "is not numeric" in resp.content

    data = 42
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert "Must be a dict" in resp.content

    data = []
    resp = api.post('nulltest', data)
    assert resp.status_code == 400
    assert "Must be a dict" in resp.content

    inst = models.Institution.objects.create(name='inst', active=True)
    data = {
        'name': 'users',
        'founded': '2014-12-31',
        'institution_id': inst.id,
        'email': 'email@example.com',
    }
    resp = api.post('groups', data)
    assert resp.status_code == 201

    data['members'] = {}
    resp = api.post('groups', data)
    assert resp.status_code == 400
    assert "is not a list-like" in resp.content

    data['members'] = []
    resp = api.post('groups', data)
    assert resp.status_code == 201

    data['institution_id'] = 'http://127.0.0.1:8000/wrong/1/'
    resp = api.post('groups', data)
    assert resp.status_code == 400
    assert "does not correspond to the collection" in resp.content

    data['institution_id'] = inst.id
    resp = api.post('groups', data)
    assert resp.status_code == 201

    data['founded'] = 'illegal date'
    resp = api.post('groups', data)
    assert resp.status_code == 400
    assert "cannot be converted into a date object" in resp.content

    data['founded'] = '2014-12-31'
    resp = api.post('groups', data)
    assert resp.status_code == 201

    del data['founded']
    resp = api.post('groups', data)
    assert resp.status_code == 201
    body = resp.json()
    today = datetime.now().strftime('%Y-%m-%d')
    assert body['founded'] == today

    data['email'] = 'invalid email'
    resp = api.post('groups', data)
    assert resp.status_code == 400
    assert "is not a valid email" in resp.content


def test_pagination(client):
    api = client.copy(prefix='/api/prefix/')
    for i in range(1, 21):
        name = 'inst%s' % (i % 10)
        active = i % 2
        models.Institution.objects.create(name=name, active=active)

    resp = api.get('institutions', {'limit': 10, 'offset': 0})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    assert [inst['id'] for inst in body] == range(1, 11)

    resp = api.get('institutions', {'limit': 10})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    assert [inst['id'] for inst in body] == range(1, 11)

    resp = api.get('institutions', {'offset': 0})
    assert resp.status_code == 400

    resp = api.get('institutions', {'limit': 10, 'offset': 10})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    assert [inst['id'] for inst in body] == range(11, 21)

    resp = api.get('institutions', {'limit': 10, 'offset': 15})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 5
    assert [inst['id'] for inst in body] == range(16, 21)

    resp = api.get('institutions',
                   {'limit': 10, 'offset': 0, 'ordering': 'active'})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    assert [inst['id'] for inst in body] == range(2, 21, 2)


def test_pagination_default_limit(client):
    models.User.objects.create_user('admin', role='admin', token='ADMINTOKEN')

    api = client.copy(prefix='/api/prefix', auth_token='ADMINTOKEN')
    for i in range(1, 21):
        title = 'title%s' % (i % 10)
        body = 'body'
        models.Post.objects.create(title=title, body=body)

    resp = api.get('posts', {'limit': 10, 'offset': 0})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 10
    assert [inst['id'] for inst in body] == range(1, 11)

    resp = api.get('posts', {'offset': 0})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 5
    assert [inst['id'] for inst in body] == range(1, 6)

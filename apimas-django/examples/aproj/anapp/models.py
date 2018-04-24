from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

Nothing = type('Nothing', (), {'__repr__': lambda self: 'Nothing'})()


INSTITUTION_CATEGORIES = [
    ["Institution", "Institution"],
    ["Research", "Research Center"]
]

class Institution(models.Model):
    name = models.TextField()
    active = models.BooleanField()
    category = models.CharField(
        choices=INSTITUTION_CATEGORIES, max_length=100, default='Research')
    logo = models.FileField(upload_to='logos/')


class User(AbstractUser):
    role = models.CharField(max_length=20)
    token = models.CharField(max_length=255, unique=True)

    @classmethod
    def apimas_create(cls, *args, **kwargs):
        return cls.objects.create_user(*args, **kwargs)

    def apimas_update(self, update_args):
        password = update_args.pop('password', Nothing)
        for key, value in update_args.iteritems():
            setattr(self, key, value)

        if password is not Nothing:
            self.set_password(password)
        self.save()

    @property
    def apimas_roles(self):
        return [self.role]


class EnhancedUser(models.Model):
    user = models.OneToOneField(User)
    is_verified = models.BooleanField()
    verified_at = models.DateTimeField(null=True)
    feature = models.CharField(max_length=255)
    institutions = models.ManyToManyField(Institution)

    @staticmethod
    def is_own(context):
        auth_user = context.extract('auth/user')
        return models.Q(user=auth_user)

    @staticmethod
    def set_verification(backend_input, instance, context):
        assert instance is None
        auth_user = context.extract('auth/user')
        backend_input['is_verified'] = bool(
            auth_user and auth_user.role == 'admin')


filter_enhanced_admins = models.Q(user__role='admin')


class UUIDResource(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    value = models.CharField(max_length=100)
    institutions = models.ManyToManyField(Institution)


class Group(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField()
    founded = models.DateField()
    active = models.BooleanField()
    email = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution, null=True, on_delete=models.PROTECT)


class Feature(models.Model):
    name = models.CharField(max_length=100)
    group = models.ForeignKey(Group)


class Variants(models.Model):
    en = models.TextField()
    el = models.TextField()


class Member(models.Model):
    username = models.TextField()
    age = models.IntegerField()
    group = models.ForeignKey(Group, related_name='members')
    name_variants = models.ForeignKey(Variants, null=True)


class Post(models.Model):
    title = models.TextField()
    body = models.TextField()
    status = models.CharField(max_length=100)


class PostLog(models.Model):
    post_id = models.BigIntegerField()
    action = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)


def post_create_post(post, context):
    auth_user = context.extract('auth/user')
    username = auth_user.username
    PostLog.objects.create(post_id=post.id, action='create', username=username)


def post_delete_post(raw_response, context):
    assert raw_response is None
    pk = context.extract('request/meta/kwargs/pk')
    auth_user = context.extract('auth/user')
    username = auth_user.username
    PostLog.objects.create(post_id=pk, action='delete', username=username)


class Nulltest(models.Model):
    fdef = models.IntegerField(null=True)
    fnodef = models.IntegerField(null=True)
    fstr = models.CharField(max_length=100)
    fbool = models.BooleanField()

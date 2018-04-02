from django.db import models
import uuid

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


class User(models.Model):
    username = models.TextField()
    age = models.IntegerField()
    group = models.ForeignKey(Group, related_name='users')
    name_variants = models.ForeignKey(Variants, null=True)


class Email(models.Model):
    email = models.TextField()
    user = models.ForeignKey(User)


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
    auth_user = context['auth']['user']
    username = auth_user.username
    PostLog.objects.create(post_id=post.id, action='create', username=username)


def post_delete_post(raw_response, context):
    assert raw_response is None
    pk = context['request']['meta']['kwargs']['pk']
    auth_user = context['auth']['user']
    username = auth_user.username
    PostLog.objects.create(post_id=pk, action='delete', username=username)


class Nulltest(models.Model):
    fdef = models.IntegerField(null=True)
    fnodef = models.IntegerField(null=True)
    fstr = models.CharField(max_length=100)
    fbool = models.BooleanField()

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

    def is_posted(self, row, context):
        return self.status == 'posted'


class Nulltest(models.Model):
    fdef = models.IntegerField(null=True)
    fnodef = models.IntegerField(null=True)

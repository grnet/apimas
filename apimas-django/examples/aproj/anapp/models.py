from django.db import models

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
    name = models.TextField()
    founded = models.DateField()
    active = models.BooleanField()
    email = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution, null=True, on_delete=models.PROTECT)


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

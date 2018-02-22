from django.db import models


class Group(models.Model):
    name = models.TextField()
    founded = models.DateField()
    active = models.BooleanField()
    email = models.CharField(max_length=100)


class Variants(models.Model):
    en = models.TextField()
    el = models.TextField()


class User(models.Model):
    username = models.TextField()
    age = models.IntegerField()
    group = models.ForeignKey(Group)
    name_variants = models.ForeignKey(Variants)


class Email(models.Model):
    email = models.TextField()
    user = models.ForeignKey(User)


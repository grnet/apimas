from django.db import models


class Group(models.Model):
    name = models.TextField()


class User(models.Model):
    username = models.TextField()
    age = models.IntegerField()
    group = models.ForeignKey(Group)


class Email(models.Model):
    email = models.TextField()
    user = models.ForeignKey(User)


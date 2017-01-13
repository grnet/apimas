from __future__ import unicode_literals

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


class UserProfile(AbstractUser):
    @property
    def apimas_roles(self):
        return self.groups.all()


class Country(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)


class City(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    country = models.ForeignKey(Country)


class Manufacturer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=10, blank=False)


class Product(models.Model):
    id = models.AutoField(primary_key=True)
    key = models.CharField(max_length=10, blank=False)
    name = models.CharField(max_length=255, blank=False)
    description = models.CharField(max_length=255, blank=False)
    stock = models.IntegerField(
        default=0, blank=False, validators=[MinValueValidator(0)])
    price = models.FloatField(
        default=0.0, blank=False, validators=[MinValueValidator(0)])
    manufacturer = models.ForeignKey(Manufacturer)


class Cart(models.Model):
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(UserProfile)
    ordered = models.BooleanField(default=False)
    products = models.ManyToManyField(
        Product, related_name='products')


class Order(models.Model):
    RECEIVED = 1
    BEING_PROCESSED = 2
    DELIVERED = 3

    ORDER_STATUSES = {RECEIVED, BEING_PROCESSED, DELIVERED}

    id = models.AutoField(primary_key=True)
    status = models.IntegerField()
    date = models.DateTimeField()
    city = models.ForeignKey(City)
    street_addres = models.CharField(max_length=255, blank=False)
    cart = models.OneToOneField(Cart)

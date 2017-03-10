# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.auth.models
import django.utils.timezone
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(null=True, verbose_name='last login', blank=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, max_length=30, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, verbose_name='username')),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('ordered', models.BooleanField(default=False)),
                ('customer', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Manufacturer',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('status', models.IntegerField()),
                ('date', models.DateTimeField()),
                ('street_addres', models.CharField(max_length=255)),
                ('cart', models.OneToOneField(to='eshop.Cart')),
                ('city', models.ForeignKey(to='eshop.City')),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('key', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=255)),
                ('description', models.CharField(max_length=255)),
                ('stock', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ('price', models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)])),
                ('manufacturer', models.ForeignKey(to='eshop.Manufacturer')),
            ],
        ),
        migrations.AddField(
            model_name='city',
            name='country',
            field=models.ForeignKey(to='eshop.Country'),
        ),
        migrations.AddField(
            model_name='cart',
            name='products',
            field=models.ManyToManyField(related_name='products', to='eshop.Product'),
        ),
    ]

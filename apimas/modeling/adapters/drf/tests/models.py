from django.db import models


class MyModel(models.Model):
    string = models.CharField(blank=False, null=False, max_length=255)
    text = models.TextField()
    email = models.EmailField()
    number = models.IntegerField()
    big_number = models.BigIntegerField()
    float_number = models.FloatField()
    boolean = models.BooleanField()
    date_field = models.DateField()
    datetime_field = models.DateTimeField()


class ModelFile(models.Model):
    file_field = models.FileField(upload_to='foo')


class OneToOneModel(models.Model):
    onetoone = models.OneToOneField(MyModel, null=True)


class ManyToManyModel(models.Model):
    manytomany = models.ManyToManyField(MyModel)


class RefModel(models.Model):
    mymodel = models.ForeignKey(MyModel, null=True)


class RefRefModel(models.Model):
    refmodel = models.ForeignKey(RefModel, null=True)

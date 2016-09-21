APIMAS
=====

# API Modeling mechanism

API Modeling mechanism provides an intuitive way to build scalable REST APIs
taking advantage of [Django Rest Framework](http://www.django-rest-framework.org/)
The goal of this mechanism is to provide an easy way for building, modifying and
extending a REST API without the cumbersome management due to application
complexity.

## Quickstart

First, you have to define your django model with your fields and their constraints:

```python
class MyModel(models.Model):
    id = models.AutoField(primary_key=True)
    age = models.IntegerField(blank=False)
    price = models.FloatField(blank=False)


class MyModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    number = models.FloatField(blank=False)
    another_moddel = models.ForeignKey(AnotherModel)
```

### API Configuration
-----------------

Subsequently, you have to specify a configuration object of your model.
This can be a python dictionary or class which defines how your model's fields
will be treated by the API, e.g. exposed fields, read only fields, filter fields, validations,
etc.

```
my_model_resource = {
     'model': 'myapp.models.MyModel',
     'fields': ('id', 'url', 'name', 'number'),
     'read_only_fields': ('id', 'url'),
     'filter_fields': ('name',),
     'allowable_operations': ('list', 'retrieve', 'create', 'update', 'delete') # This is default
}

API_SCHEMA = {
    'resources': {
         'myresource': my_model_resource
    }
}
```

Then just create the corresponding view:

```
from apimas.container import Container
from myapp.models import MyModel

container = Container('myapi')
view = container.create_view('myresource', MyModel, my_model_resource)
url_patterns = [view]

## your code
```

or simply

```
url_patterns = [container.create_api_views(API_SCHEMA)] # In case of multiple resources.
```
At the end of this procedure, you easily created the following endpoints:

```
GET https://localhost/myapi/myresource/
POST http://localhost/myapi/myresource/
GET http://localhost/myapi/myresource/<pk>/
PUT http://localhost/myapi/myresource/<pk>/
DELETE http://localhost/myapi/myresource/<pk>/
```

APIMAS
=====

# API Modeling mechanism

API Modeling mechanism provides an intuitive way to build scalable REST APIs
taking advantage of [Django Rest Framework](http://www.django-rest-framework.org/).
The goal of this mechanism is to provide a flexible way for building, modifying and
extending a REST API without the cumbersome management due to the application
complexity.


## Usage

First, define your django model with their fields and their constraints:
```
class AnotherModel(models.Model):
    id = models.AutoField(primary_key=True)
    age = models.IntegerField(blank=False)
    price = models.FloatField(blank=False)


class MyModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    number = models.FloatField(blank=False)
    another_model = models.ForeignKey(AnotherModel)
```


### API Configuration

Subsequently, you have to specify a configuration object of your model.
This can be a python dictionary or class which defines the resource's fields
and their properties, e.g. read only, required, etc. and how these fields are
treated by the API, e.g. filter fields, allowable methods, etc.

There are three levels of your API configuration:
- `field_schema`: The level where you setup the fields for a specific resource
  along with their properties, validations, etc.
- `resource_schema`: One level higher than `field_schema`. This level configures
  your resource in terms of authentication, authorization, allowable methods,
  filtering options, etc.
- `api_schema`: API schema consists of all resources and their global settings
  (see below).

A simple example illustrating api configuration:
```
field_schema: {
     'fields': ['id', 'url', 'name', 'number'],
     'read_only_fields': ['id', 'url'],
}

resource_schema = {
     'model': 'myapp.models.MyModel',
     'field_schema': field_schema
     'filter_fields': ['name'],
     'allowable_operations': ['list', 'retrieve', 'create', 'update', 'delete'] # This is default
}

API_SCHEMA = {
    'global': {
        # global settings here.
    }
    'resources': {
        'myresource': my_model_resource,
        # another resources here.
    }
}
```

Then, all you have to do is to create the corresponding view using
`modeling.Container` class:
```
from apimas.modeling.container import Container
from myapp.models import MyModel

container = Container('myapi')
# Create view for a single resource.
view = container.create_view('myresource', MyModel, my_model_resource)
url_patterns = [view]

## your code
```

or simply:
```
# Create views for your whole API.
url_patterns = [container.create_api_views(API_SCHEMA)]
```

At the end of this procedure, you easily created the following endpoints:
```
GET https://localhost/myapi/myresource/
POST http://localhost/myapi/myresource/
GET http://localhost/myapi/myresource/<pk>/
PUT http://localhost/myapi/myresource/<pk>/
PATCH http://localhost/myapi/myresource/<pk>/
DELETE http://localhost/myapi/myresource/<pk>/
```


### Field Schema

By determining the `field_schema` key on your resource schema, you define
the list of your fields which are exposed to the API along with their
properties and validations.

They are two ways of specifying these properties:
- List fields with common properties (supported keys are `read_only_fields`,
  `write_only_fields`, `required_fields`, `nullable_fields`,
  `blankable_fields`).
- Delineate properties of each field (via `properties` key).

Example:
```
'field_schema': {
    'fields': ['id', 'url', 'name'],
    'read_only_fields': ['id', 'url'],
    'write_only_fields': ['name'],
    'required_fields': ['name'],
    'nullable_fields': ['price'],
    'properties': {
        'name': {
            'write_only': True,
            'allow_null': False,
            'validators' = [my_validator,]
        }
        'price': {
            'read_only': True,
            'allow_null': False,
            'validators' = [my_validator,]
        }
    }
}
```

Supported listing properties:
 - `read_only_fields`
 - `write_only_fields`
 - `required_fields`
 - `nullable_fields`
 - `blankable_fields`

Supported attributes:
 - `allow_null`,
 - `allow_blank`,
 - `allow_empty`,
 - `required`,
 - `read_only`,
 - `write_only`,
 - `help_text`,
 - `label`,
 - `error_messages`,
 - `validators`,


### Nested objects

You are also able to define nested objects inside your field schema.

Example:
```
'field_schema': {
    'fields': ['id', 'url', 'name', 'another_model'],
    'nested_objects': {
        'another_model': {
            'model_field': 'another_model',
            'field_schema': {
                'fields': ['id', 'age', 'price'],
                 # Your schema....
            }
        }
    }
}
```

Note that 'another_model' key inside the corresponding dictionary references to
the api field name of your object, whereas the value of `model_field` key
indicates the model field name which is related to another model. Therefore,
you can name your api field whatever you like. Don't worry; API Modeling mechanism
will inspect the `model_field` and find which type of relation is underlying.


### Authentication and Permissions

You define your authentication and permission classes as stated here:
 - [http://www.django-rest-framework.org/api-guide/authentication/](http://www.django-rest-framework.org/api-guide/authentication/)
 - [http://www.django-rest-framework.org/api-guide/permissions/](http://www.django-rest-framework.org/api-guide/permissions/)

Example:
```
my_resource_schema = {
    'my_resource': {
        'authentication_classes': ['rest_framework.authentication.BasicAuthentication', 'myapp.authentication.YourAuthenticationClass', ]
        'permission_classes': ['rest_framework.permissions.IsAuthentication', 'myapp.permissions.YourPermissionClass', ]
        'field_schema': {
             # Your field schema configuration ...
        }
    }
}
```


### Filtering

API Modeling Mechanism supports three kinds of filtering.

#### Simple equality-based filtering

Example:
```
my_resource_schema = {
    'my_resource': {
        'filter_fields': ['name', 'price']
        'field_schema': {
             # Your field schema configuration ...
        }
    }
}
```

```
http://myapp.com/myapi/my_resource?name=foo&price=10
```

#### Search filtering

Specify a list of fields that will be searched based on the
query parameter.

Example:
```
my_resource_schema = {
    'my_resource': {
        'search_fields': ['name', 'price']
        'field_schema': {
             # Your field schema configuration ...
        }
    }
}
```

```
http://myapp.com/myapi/my_resource?search=foo
```

#### Ordering filtering

Ordering filtering enables you to control the ranking of your
results.

Example:
```
my_resource_schema = {
    'my_resource': {
        'ordering_fields': ['name']
        'field_schema': {
             # Your field schema configuration ...
        }
    }
}
```

Descending order:
```
http://myapp.com/myapi/my_resource?ordering=name
```

Ascending order:
```
http://myapp.com/myapi/my_resource?ordering=-name
```

### Custom behaviour

If you would like to override the default implementation  or to add
extra functionality on your generated `ViewSet` and `Serializer` classes, your
can intuitively do this by writing your own classes which include your custom
behaviour to the generated classes of mechanism.


Example:
```
my_resource_schema = {
    'my_resource': {
        'custom_mixins': ['myapp.views.mymodule.Myclass',]
        'field_schema': {
            'custom_mixins': ['myapp.serializers.mymodule.Myclass',]
             # Your field schema configuration ...
        }
    }
}
```

Observe that the deeper `custom_mixins` references to the classes that add
functionality to the generated `Serializer` class, whereas the outer
`custom_mixins` indicates classes bounded to the `ViewSet` class.


### Global configuration

You are able to define settings concerning all resources of your API.
At the moment, supported settings are:
 - `authentication_classes`
 - `permission_classes`
 - `hyperlinked`

Example:
```
api_schema = {
    'global': {
        # your global settings here.
    }
    'resources': {
        # your resources here.
    }
}
```


### Hook classes
Hook classes are intended to provide hooks for embedding the business logic
of resources before and after any CRUD operation.

Example:
```
from apimas.modeling.mixins import HookMixin


class MyHookClass(HookMixin):
    def preprocess_create(self):
        """ This code is executed before the creation of a resource"""
        # Code here
        # Stash your changes
        self.stash(**kwargs)

    def finalize_create(self):
        """ This code is executed after the creation of instance. """
        # Unstash your changes.
        self.unstash()
        # Code and any business logic with the created instance.
```

Then define `hook_class` attribute on your resource schema:
```
my_resource_schema = {
    'my_resource': {
        'hook_class': 'myapp.MyHookClass',
        'field_schema': {
             # Your field schema configuration ...
        }
    }
}
```


## Client Generation

After building your API fulfilling the given specification, you can also
easily create client objects to interact with it.


### Create clients for all API resources

`ApimasClientAdapter` supports the creation of client objects for all your
resources of your `APIMAS` specification.

```
from apimas.modeling.clients import ApimasClientAdapter
adapter = ApimasClientAdapter('http://localhost:8000/')
# Prepare adapter for creating clients according to given spec.
adapter.construct(spec)
adapter.apply()
```

The above code will generate a dictionary keyed by the resource name which
contains a partially created client object, corresponding to this resource
and its schema. However, afterwards, you have to explicitly pass credentials
to consume each resource.

```
client = adapter.get_client('myresource')
client.set_credentials('basic', username='username', password='password')
client.list()
```

Therefore, you are able to perform any CRUD operations. Data can be passed
as dictionary for UPDATE and CREATE operations. Moreover, LIST and
RETRIEVE operations support query parameters (defined as dictionary too).
Finally, your can also define your request headers.

```
# Create a new resource with name='test' and number=10 passed in the HTTP request body.
# Request: POST myresource/
response = client.create(data={'name': 'test', 'number': 10})

# Update resource with id `1` and replace its data as name='test' and number=10
# Request: PUT myresource/1/
response = client.update(1, data={'name': 'test', 'number': 10})

# Update only a subset of fields of resource with id `1`.
# Request: PATCH myresource/1/
response = client.partial_update(1, data={'name'='new name'})

# Get all resources with name='test'
# Request: GET myresource/?name=test&number=10
response = client.list(params={'name': 'test', 'number': 10})

# Get resource with id `1`
# Request: GET myresource/1/
response = client.retrieve(1)

# Delete resource with id `1`.
# Request: DELETE myresource/1/
response = client.delete(1)
```

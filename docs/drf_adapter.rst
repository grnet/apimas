Create server-side applications
*******************************

You can easily build a server-side application by using an APIMAS
backend. Currently, the only backend supported is ``apimas-drf``
which is uses `django rest framework`_ to build REST APIs on top of
a `django`_ application.

.. _django rest framework: http://www.django-rest-framework.org/
.. _django: https://www.djangoproject.com/

Installation
============
In a virtualenv, run the following command to install apimas-drf:

.. code-block:: console

    pip install apimas-drf


Quickstart-Create a django application
=======================================

At this point, we assume that you are familiar with django basic
concepts and have some experience with developing django applications.

Starting point
--------------

As a starting point, you have to define your django models.
Based on your models and your specification,
APIMAS will create the classes implementing the application's REST API.

According to the guide in `section <writing_spec.html>`__, you can
specify a collection of resources named `foo`, where all REST
operations are allowed:


.. code-block:: python

    API_SPEC = {
        'api': {
            '.endpoint': {},
            'foo': {
                '.collection': {},
                '*': {
                    'text': {
                        '.string': {}
                    },
                    'number': {
                        '.integer': {},
                    },
                },
                'actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {},
                }
            }
        }
    }

Given the specification above, you have to create the corresponding
django-model in the project's ``models.py`` file.

.. code-block:: python

    from django.db import models

    class Foo(models.Model):
        text = models.CharField(max_length=20)
        number = models.IntegerField()

Enrich APIMAS specification
---------------------------

In order to link the specification of the collection to the django model
you have to declare `'foo'` as a `django rest framework` collection
and `text` and `number` as fields, using the predicates
``.drf_collection`` and ``.drf_field``, respectively:

.. code-block:: python

         API_SPEC = {
        'api': {
            '.endpoint': {},
            'foo': {
                '.collection': {},
                '.drf_collection': {
                    'model': 'myapp.models.Foo'
                },
                '*': {
                    'text': {
                        '.string': {},
                        '.drf_field': {},
                    },
                    'number': {
                        '.integer': {},
                        '.drf_field': {},
                    },
                },
                'actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {},
                }
            }
        }
    }

In the above example, we introduced two new predicates which are not
included in the APIMAS standard predicates: a) ``.drf_collection``, b)
``.drf_field``. These predicates are understood only by the
`django-rest-framework` backend, which is responsible for implementing
this specification.


Set permissions
---------------

APIMAS provides a mechanism for setting the permissions of your
application. You can read more in a next section. However, for this
tutorial, we omit the description of this mechanism. Thus, you have to
add the following configuration on your specification.


.. code-block:: python

         API_SPEC = {
        'api': {
            '.endpoint': {
                'permissions': [
                    # That is (collection, action, role, field, state, comment).
                    ('foo', '*', 'anonymous', '*', '*', 'Just an example')
                ]
            },
            'foo': {
                '.collection': {},
                '.drf_collection': {
                    'model': 'myapp.models.Foo'
                },
                '*': {
                    'text': {
                        '.string': {},
                        '.drf_field': {},
                    },
                    'number': {
                        '.integer': {},
                        '.drf_field': {},
                    },
                },
                'actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {},
                }
            }
        }
    }

This tells APIMAS, that an anonymous user can perform any action ('*'
on 2nd column) on collection 'foo', associated with any field ('*' on
4th column) and any state ('*' 5th column). The last column is used to
write your comments. More about permissions can be found
`here <drf_adapter.html#apimas-permissions>`__.


Use DjangoRestAdapter
---------------------

Then, APIMAS will create all required code using ``DjangoRestAdapter``
class. In particular, ``DjangoRestAdapter`` will create the  mapping
of URL patterns and views (``urlpatterns``). This mapping is
specified specify on your ``URLconf`` module (typically, the
``urls.py`` file on your django-project).

For example, in ``urls.py`` file:

.. code-block:: python
    
    from apimas.drf.django_rest import DjangoRestAdapter
    from myapp.spec import API_SPEC

    adapter = DjangoRestAdapter()
    adapter.construct(API_SPEC)

    urlpatterns = [
        adapter.urls
    ]

Now, you are ready to test your application, by running:

.. code-block:: shell

    python manage.py runserver

You can make some testing calls using ``curl``. For example, create a
new resource object

.. code-block:: shell

    curl -X POST -d '{"text": "foo", "number": 1}' -H "Content-Type: application/json" http://localhost:8000/api/foo/

.. code-block:: json

    {
        "number": 1, 
        "text": "foo"
    }

or, retrieve an existing one:

.. code-block:: shell

    curl -X GET http://localhost:8000/api/foo/1/

.. code-block:: json

    {
        "number": 1, 
        "text": "foo"
    }

django-rest-framework adapter
=============================

So far, we have seen a short tutorial on using APIMAS to create a
`django` application. We easily created an application which served a
REST API, by only defining the storage django-models) and the view
(APIMAS specification, i.e. API representation) representation of our
application. Typically, apart from the django-models,
a django-developer has to create the corresponding django forms and
views in order to map url patterns with implementation. Hence, for a
typical example a developer has to make the following classes:

``models.py``:

.. code-block:: python

    from django.db import models

    class Foo(models.Model):
        text = models.CharField(max_length=30)
        number = models.IntegerField()

``forms.py``
.. code-block:: python

    from django import forms
    from myapp.models import Foo

    class FooForm(forms.ModelForm):
        
        class Meta(object):
            model = Foo
            fields = ('number', 'text',)

``views.py``
.. code-block:: python

   import json
   from django.http import HttpResponse
   from myapp.forms import FooForm

   def view_foo(request):
       form = FooForm()
       return render(request, 'path/to/template', form)

Even when using `django-rest-framework` which facilitates the
development of the REST API, the developer typically has to create
boilerplate such as:

``serializers.py``

.. code-block:: python

    from rest_framework import serializers
    from myapp.models import Foo

    class FooSerializer(serializers.ModelSerializer):

        class Meta:
            model = Foo
            fields = ('number', 'text')

``views.py``

.. code-block:: python

    from rest_framework import viewsets
    from myapp.serializers import FooSerializer
    from myapp.models import Foo

    class FooViewSet(viewsets.ModelViewSet):
        serializer_class = FooSerializer
        queryset = Foo.objects.all()

Even though in the above examples things seem to be easy, the
management of such an application may become cumbersome if more entities
are introduced or the complexity of data representation of an entity is
increased, e.g. if we have an entity with 30 fields, and each field
behaves differently according to the state of the entity (e.g.
non-accessible in read operations).

As already mentioned in a previous section, APIMAS provides a way to
describe your application and its data representation on a document.
The `django-rest-adapter` reads from the specification and it
translates the description of your application into implementation.
The `django-rest-adapter` uses `django-rest-framework` behind the
scenes and generates at runtime the required
``rest_framework.serializers.Serializer`` (responsible for the
serialization and deserialization of your request data) and
``rest_framework.viewsets.ViewSet`` classes according to the
specification.

In essence, your application consists of your storage and API
representation, and each time, you want to change something on your
API representation, you simply refer to the corresponding properties
of your specification. 

django-rest adapter's workflow
------------------------------
The `django-rest` adapter creates the corresponding mapping of url
patterns to views based on the storage and API representation of your
application. Therefore, for a typical application we have the
following work flow:

- In a list operation (``GET <collection name>/``), the list of
  objects included in the model associated with the collection, is
  retrieved.
- In a retrieve operation (``GET <collection name>/<pk>/``), a single
  model instance is displayed based on its API representation.
- In a create operation (``POST <collection name>/``), sent data are
  validated, and then a model instance is created after serializing
  data.
- In an update operation (``PUT|PATCH <collection name>/pk/``), sent
  data are validated, serialized, and the new values of model instance
  are set.
- In a delete operation (``DELETE <collection name>/pk/``), a model
  instance, identified by the ``<pk>`` is deleted.


Customize your application
--------------------------

If the default behaviour above does not suit the application,
you are able to customize and extent it by adding your own logic.
Specifically, APIMAS provides two hooks for every action
(before interacting with the database and after)
for extending the logic of your application or executing arbitrary code
(e.g. executing a query or sending an email to an external agent).
You can do this as follows:

.. code-block:: python

    from apimas.drf.mixins import HookMixin

    class RestOperations(HookMixin):
    
        def preprocess_create(self):
            # Code executed after validating data and before creating
            # a new instance.
            ...

        def finalize_create(self):
            # Code executed after creating the model instance and
            # and before serving the response.
            ...

If you want to customize the behaviour of your application in other
actions, you simply have to add the corresponding methods to your
class, e.g.

- ``preprocess_<action_name>(self)`` (for executing code before
  interacting with db)
- ``finalize_<action_name>(self)`` (for executing code before
  serving the response and after interacting with db).

Customize your application - A simple case scenario
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Imagine that we have the following model:

.. code-block:: python

    from django.db import models

    class Foo(models.Model):
        text = models.CharField(max_length=30)
        number = models.IntegerField()
        another_text = models.CharField(max_length=30)

and the API specification for this model:

.. code-block:: python

    API_SPEC = {
        'api': {
            '.endpoint': {},
            'foo': {
                '.drf_collection': {
                    'model': 'myapp.models.Foo'
                },
                '*': {
                    'text': {
                        '.string': {},
                        '.drf_field': {}
                    },
                    'number': {
                        '.integer': {},
                        '.drf_field': {}
                    },
                },
                'actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {}
                }
            }
        }
    }

In the above example, the field ``another_text`` is not exposed to the
API, but its value is computed by the server based on the values of
``text`` and ``number``. Therefore, in this case, you may write your
hook class like below:

.. code-block:: python

    from myapp.mymodule.myfunc

    class RestOperations(HookMixin):
        def preprocess_create(self):
            context = self.unstash()
            another_text = myfunc(context.validated_data['text'],
                                  context.validated_data['number'])
            self.stash(extra={'another_text': another_value})

Here we get the context of the action via the ``self.unstash()`` method,
then we compute the value of ``another_text`` according to some
application logic, and finally, we tell APIMAS (``self.stash()``) that
it should add extra data to the model instance (``another_text``),
in addition to those sent by the client.
``self.unstash()`` returns a namedtuple with the following fields:

- ``instance``: Model instance to interact.
- ``data``: Dictionary of raw data, as sent by the client.
- ``validated_data``: Dictionary of de-serialized, validated data.
- ``extra``: A dictionary with extra data, you wish to add to your
  model.
- ``response``: Response object.

Note that in some cases, there are some context fields that are not
initialized. For instance, in the ``preprocess_create()`` hook,
``instance`` is not initialized because model instance has not been
created yet.

The last part is to declare the use of the hook class. You have to
provide an argument to the ``hook_class`` parameter of the
``.drf_collection`` predicate.

.. code-block:: python

    'foo': {
        '.drf_collection': {
            'model': 'myapp.models.Foo',
            'hook_class': 'myapp.hooks.RestOperations',
        },
        # spec as above.
    }

Write django-rest-framework code
--------------------------------

As we have already mentioned, django-rest adapter generates
dynamically two classes: a) a serializer class, b) a viewset class
according to the specification. If you still wish to customize and
override these generated classes, APIMAS provides various ways to do
that:

- Override these classes with your own classes.
- Add additional attributes.

There are two primary reasons to do this:

- django-rest adapter has not abstracted the full functionality of
  django-rest-framework yet.
- You may have reasons to override the internal functionality of
  django-rest-framework.

Below, we describe two common cases when you need to write
django-rest-framework code.

Deal with structures
^^^^^^^^^^^^^^^^^^^^

In your API, you may have structural fields, that is, all fields
characterized as ``.struct`` or ``.structarray``.
django-rest-framework backend does not support write operations, 
because they are read-only by default. Hence, if you want to be able
to perform write operations on these fields, you have to override the
``create()`` or/and ``update()`` methods, provided by each serializer
class.

Example:

.. code-block:: python

    from rest_framework.serializers import BaseSerialzer

    class MySerializer(BaseSerializer):

        def create(self, validated_data):
            # Your code
            ...

        def update(self, instance, validated_data):
            # Your code.
            ...

Then, in your specification, specify the following parameter in
``.drf_collection`` predicate:

.. code-block:: python

    'foo': {
        '.drf_collection': {
            'model': 'myapp.models.Foo',
            'model_serializers': ['myapp.serializers.MySerializer'],
        },
        # spec as above.
    }

``model_serializers`` tells APIMAS that the classes specified should
be base classes for the generated serializer class, which are placed to
the lowest level of the inheritance hierarchy. Therefore, in the above
example, the hierarchy of the generated class is as follows:

.. digraph:: foo
    
    node[shape=box];

    "BaseSerialzer" -> "MySerializer" -> "GeneratedSerializer";

If you specify more than one classes on your ``model_serializers``,
then the classes on the right will inherit the classes on the left.

Further information about writable structure fields can be found in
the official documentation of django-rest-framework, 
`here <http://www.django-rest-framework.org/api-guide/relations/#writable-nested-serializers>`__.

Add more actions to your API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can have additional actions to your API apart from the CRUD
ones you declare in the specification. For example:

.. code-block:: rest

    POST foo/1/myaction/

To implement ``myaction`` you need to write your own ViewSet class
that includes a method with the action's name. For instance:

.. code-block:: python

    from rest_framework.decorators import detail_route
    from rest_framework.viewsets import GenericViewSet

    class MyViewSet(GenericViewSet):

        @detail_route(methods=['post'])
        def myaction(self, request, pk):
            # My code.
            ..

Next, you need to include the module path of your ViewSet mixin class in
the ``mixins`` parameter of your ``.drf_collection`` predicate.
APIMAS will inherit from your class and the extra action method
will appear in the generated final ViewSet class.

.. code-block:: python

    'foo': {
        '.drf_collection': {
            'model': 'myapp.models.Foo',
            'mixins': ['myapp.mixins.MyViewSet'],
        },
        # spec as above.
    }

You can find more information about extra actions
`here <http://www.django-rest-framework.org/api-guide/viewsets/#marking-extra-actions-for-routing>`__.

.. note::

    Specifying bases and mixins for the generated viewse class
    enhances the resusability of your code. For instance, you
    may have a custom ViewSet class which is shared amongst all your
    collections. Instead of copying the same code over and over across
    different hooks, you can declare a common mixin for all of them
    within your specification.


django-rest-framework fields
----------------------------

By default, the django-rest adapter reads all REST resource properties
predicated with ``.drf_field`` and tries to map each of them to an
attribute or function on your django model.
It is not necessary to have 1 to 1 mapping between your API and storage
configuration. For instance, you may want to:

- expose a field with different name as that specified in your model.
- define fields in your API which are not intended to be stored in
  your db.
- create responses with arbitrary structure.

Examples:

Define the name of source field explicitly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In this example, we create an ``api_text`` property on a REST resource
that is mapped to a differently named ``text`` field on a django model,
using the ``source`` parameter of the ``.drf_field`` predicate:


.. code-block:: python

    from django.db import models

    class Foo(models.Model):
        text = models.CharField(max_length=30)
        number = models.IntegerField()

.. code-block:: python

    'foo': {
        '.drf_collection': {
            'model': 'myapp.models.Foo',
        },
        '*' {
            'api_text': {
                '.string': {},
                '.drf_field': {
                    'source': 'text'
                }
            },
            'number': {
                '.integer': {},
                '.drf_field': {},
            },
        },
    }

Use non-model fields
^^^^^^^^^^^^^^^^^^^^

You can create REST resource properties that are not mapped to any of
the django model fields. In the following example, we add a string
property named "extra_field" to our specification that is not to be
saved to or retrieved from the model, by specifying ``onmodel: False``
to the ``.drf_field`` predicate.

.. code-block:: python

    'foo': {
        '.drf_collection': {
            'model': 'myapp.models.Foo',
        },
        '*' {
            'api_text': {
                '.string': {},
                '.drf_field': {
                    'source': 'text'
                }
            },
            'number': {
                '.integer': {},
                '.drf_field': {},
            },
            'extra-field': {
                '.string': {},
                '.drf_field': {
                    'onmodel': False,
                },
            },
        },
    }

A non-model property is validated but there is no automatic handling of
it during write actions. You have to handle it via the hooks provided
by APIMAS.

When processing read actions such as list or retrieve, the django-rest
adapter will seek to call a function to extract the value of non-model
properties since there is no model for them.
If you want non-model fields to be readable, you must provide an
argument to the ``instance_source`` parameter on the ``.drf_field``
predicate. The parameter is enabled only when ``onmodel`` is False.
``instance_source`` must be the module path of a function that accepts
a model instance as input and returns the property value.


.. code-block:: python

    def myfunc(instance):
        # Code which retrieves the value of a non-model field based on
        # the instance.
        pk = instance.pk

        # Open a file, identified by the pk of the instance and
        # extract the desired value.
        with open('file_%s.txt' % (str(pk)), 'r') as myfile:
            data = myfile.read()
        return data
        

.. code-block:: python

    'foo': {
        '.drf_collection': {
            'model': 'myapp.models.Foo',
        },
        '*' {
            'api_text': {
                '.string': {},
                '.drf_field': {
                    'source': 'text'
                }
            },
            'number': {
                '.integer': {},
                '.drf_field': {},
            },
            'extra-field': {
                '.string': {},
                '.drf_field': {
                    'onmodel': False,
                    'instance_source': 'myapp.mymodule.myfunc'
                },
            },
        },
    }

Create structured responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Apart from the things already mentioned, one additional reason for
having non-model fields is to create responses with arbitrary structure.
For instance, instead of returning the following response:

.. code-block:: json

    {
        "text": "foo",
        "number": 10
    }

you wish to return this:

.. code-block:: json

    {
        "data": {
            "text": "foo",
            "number": 10
        }
    }

Your django-model is not aware of the node "data".
Therefore, you need to format your specification as:

.. code-block:: python

    'foo': {
        '.drf_collection': {
            'model': 'myapp.models.Foo',
        },
        '*' {
            'data': {
                '.drf_field': {'onmodel': False},
                '.struct': {
                    'api_text': {
                        '.string': {},
                        '.drf_field': {
                            'source': 'text'
                        }
                    },
                    'number': {
                        '.integer': {},
                        '.drf_field': {},
                    },
                }
            }
        },
    }

where node "data" is a structured non-model property consisting
of model fields "api_text" and "number".

.. warning::

    All fields on a model must be exposed to the same REST location.
    They must not be scattered among different nodes in the
    specification.

APIMAS permissions
------------------

APIMAS implements a built-in mechanism for setting permissions to your
server-side application. The permissions of your application consist
of a set of rules. Each rule contains the following information:

- ``collection``: The name of the collection to which the rule is
  applied.
- ``action``: The name of the action for which the rule is valid.
- ``role``: The role of the user (entity who performs the request)
  who is authorized to make request calls.
- ``field``: The set of fields that are allowed to be handled in this
  request (either for writing or retrieval).
- ``state``: The state of the collection which **must** be valid when
  the request is performed.
- ``comment``: Any comment for documentation reasons.

Set permission rules
^^^^^^^^^^^^^^^^^^^^
Consider the following example rule:

.. code-block:: python

    rule = ('foo', 'create', 'admin', 'text', 'open', 'section 1.1')

The rule indicates that a request for the collection `foo`,
which is asking to `create` a new resource, and is issued by an `admin`,
is allowed to create a `text` property when the collection is in
an `open` state. `section 1.1` is a comment made by the developer and
it is ignored.

To enable writing another field `number`, write one more rule:

.. code-block:: python

    rule = ('foo', 'create', 'admin', 'text', 'open', 'section 1.1')
    rule2 = ('foo', 'create', 'admin', 'number', 'open', 'section 1.1')

or write a pattern to match the two properties:

.. code-block:: python

    rule = ('foo', 'create', 'admin', 'text|number', 'open', 'section 1.1')

Supported APIMAS operators for matching are:

- ``*``: Any pattern.
- ``?``: Pattern indicated by a regular expression.
- ``_``: Pattern starts with the given input.
- ``!``: NOT operation.
- ``&``: AND operation.
- ``|``: OR.

For example, the following rule reveals that an admin or a member
('admin|member') can perform any ('*') action any on collection starts
wit 'foo' ('_foo'), provided that they handle fields matched with a
particular expression ('?ition$') and the state is 'open' and 'valid'
at the same time ('open&valid').

.. code-block:: python

    rule = ('_foo', '*', 'admin|member', '?ition$', 'open&valid', 'section 1.1')

The set of your rules must be declared in your specification as a
parameter to the ``.endpoint`` predicate.

Example:

.. code-block:: python

    {
        'api': {
            '.endpoint': {
                'permissions': [
                    ('foo', 'create', 'admin', 'text', 'open', 'section 1.1'),
                    # More rules...
                    ...
                ]
            }
        },
    }

APIMAS permissions -- Roles
^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to check against the roles specified in permission rules, you
have assign to roles to an authenticated user by setting them as a list of
strings named ``apimas_roles`` on your user instance as in:

.. code-block:: python

    request.user.apimas_roles = ['admin', 'dev']


.. code-block:: python

    class User(models.Model):
         ...

         @property
         def apimas_roles(self):
             ... 

Unauthenticated users
"""""""""""""""""""""

Requests by unauthenticated users are matched by the ``anonymous`` role
in permission rules. Using anonymous roles you can make part of your API
public. For example, the following rule allows anyone to create ``foo``
resources as long as ``foo`` is in an ``open`` state:

.. code-block:: python

    rule = ('foo', 'create', 'anonymous', '*', 'open', 'section 1.1')

APIMAS permissions -- Fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The 'field' column of a rule, corresponding to field, indicates which
field(s) are allowed to be handled. For instance:

- For a write-operation, only the fields defined in your rules are
  allowed to be written. Thus, if someone sent some data that are not
  validated against your rules, they would be ignored.
- For a read-operation, only the fields defined in your rules can be
  accessed. The rest are not displayed to the client.

APIMAS permissions -- States
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

States are matched if calling a class method on the model associated
with the request returns true. There is a different method for checking
a state for collection (list, create) versus resource requests.
The names and signatures of the methods are as follows:

.. code-block:: python

    @classmethod
    def check_collection_state_<state name>(cls, row, request, view):
        # your code. Return True or False.
        ...

    @classmethod
    def check_resource_state_<state name>(cls, obj, row, request, view):
        # your code. Return True or False.
        ...

For example, imagine you have the following permission rules:

.. code-block:: python

    rule = ('foo', 'create', 'anonymous', '*', 'open', 'section 1.1')
    rule2 = ('foo', 'update', 'anonymous', 'number', 'submitted', 'section 1.1')

In the above example, in the case of an update operation, the methods
listed below will be triggered to check if states 'open' or
'submitted' are satisfied:

- ``check_state_collection_open()``
- ``check_state_resource_submitted()``

If none of the states is matched, then an HTTP_403 error is returned. If
only one state is matched, then the django-rest adapter checks which
fields can be handled in this state, e.g. when the state is 'open', an
anonymous user can set all fields, while when the state is
'submitted' only the field 'number' can be updated.

django-rest adapter predicates
------------------------------

Below, there is a list of the predicates introduced by the django-rest
adapter along with their semantics.


=================== =====================================================================================
Predicate           Description
=================== =====================================================================================
``.drf_collection`` The parent node is a collection of resources of the same type,
                    where each resource can be related to other resources, it is
                    described by some data, and there are actions that can be
                    performed on it. The parent node uses `django-rest-framework`
                    backend.

                    **Parameters**:
                        `model`: String of the django-model corresponding to
                        the storage representation of the collection.

                        `authentication_classes`: (optional) List of classes
                        used for the authentication of the collection.
                        More `here <http://www.django-rest-framework.org/api-guide/authentication/>`__.

                        `permission_classes`: (optional) List of the classes
                        responsible for the permissions of the collection.
                        More `here <http://www.django-rest-framework.org/api-guide/permissions/>`__.

                        `mixins`: (optional) List of the bases classes of
                        the ``ViewSet`` class generated by django-rest adapter.

                        `model_serializers`: (optional) List of bases classes
                        of the ``ApimasModelSerializer`` (class responsible when
                        having model-fields) generated by django-rest adapter.

                        `serializers`: (optional) List of base classes of
                        the ``ApimasSerializer`` (class responsible when
                        having non-model fields) generated by django-rest adapter.

                        `hook_class`: (optional) A class which implements hooks
                        before and after interacting with db for various actions.
                        See `more <#customizing-your-application>`__.

``.drf_field``      The parent node is a drf_field. In other words, it is an
                    instance of a django-rest-framework field which is responsible
                    for converting raw value of a field (sent by client) into
                    complex data such as objects, querysets, etc.

                    **Parameters**:
                        `onmodel`: True if field has a storage representation,
                        False otherwise (default: True).

                        `source`: Name of the storage representation of
                        the field (Default is the name of the parent).

                        `instance_source`: A string which points to a function
                        which retrieves the value of the field given the
                        current instance (applicable if ``onmodel: False``). 
=================== =====================================================================================

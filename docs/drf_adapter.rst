Create server-side applications
*******************************

You can easily build a server-side application by using a backend
which supports APIMAS. Currently, there is a package named ``apimas-drf``
which taking advantage of `django rest framework`_ framework to build REST
APIs on top of a `django`_ application.

.. _django rest framework: http://www.django-rest-framework.org/
.. _django: https://www.djangoproject.com/

Installation
============
In a virtualenv, run the following command to install apimas-drf:

.. code-block:: console

    pip install apimas-drf


Quickstart-Create a django application
=======================================

At this point, it is assumed that your are familiar with django basic
concepts and have a little experience with developing django
applications.

Starting point
--------------

As a starting point, you have to define your django-models. These are
the base of your application, and based on that and specification,
APIMAS will generate code implementing your application's REST API.

Note that we have already created an APIMAS specification based on the
guide in this `section <writing_spec.html>`__. Thus, imagine we have a
collection of resources named `foo`, where all REST operation are
allowed.


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

Given that specification, you have to create the corresponding
django-model on your ``models.py`` file.

.. code-block:: python

    from django.db import models

    class Foo(models.Model):
        text = models.CharField(max_length=20)
        number = models.IntegerField()

Enrich APIMAS specification
---------------------------

What is next, all you have to do is to define `'foo'` as a collection
which use `django rest framework` backend and `text` and `number`, the
corresponding fields that are exposed to the API.

To do that, enrich your specification as follows:

.. code-block:: python
    :emphasize-lines: 6,7,8,12,16

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
`django-rest-framework` backend, which is responsible for translating
this specification on implementation.


Set permissions
---------------

APIMAS provides a mechanism for setting the permissions of your
application. You can read more in a next section. However, for this
tutorial, we omit the description of this mechanism. Thus, you have to
add the following configuration on your specification.


.. code-block:: python
    :emphasize-lines: 3,4,5

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

Example:

.. code-block:: python
    :caption: urls.py
    
    from apimas.modeling.adapters.drf.django_rest import DjangoRestAdapter
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

.. code-block:: python
    :caption: models.py

    from django.db import models

    class Foo(models.Model):
        text = models.CharField(max_length=30)
        number = models.IntegerField()

.. code-block:: python
    :caption: forms.py

    from django import forms
    from myapp.models import Foo

    class FooForm(forms.ModelForm):
        
        class Meta(object):
            model = Foo
            fields = ('number', 'text',)

.. code-block:: python
   :caption: views.py

   import json
   from django.http import HttpResponse
   from myapp.forms import FooForm

   def view_foo(request):
       form = FooForm()
       return render(request, 'path/to/template', form)

Even when using `django-rest-framework` which facilitates the
development of the REST API, the developer typically has to create
something like the following:

.. code-block:: python
    :caption: serializers.py

    from rest_framework import serializers
    from myapp.models import Foo

    class FooSerializer(serializers.ModelSerializer):

        class Meta:
            model = Foo
            fields - ('number', 'text')

.. code-block:: python
    :caption: views.py

    from rest_framework import viewsets
    from myapp.serializers import FooSerializer
    from myapp.models import Foo

    class FooViewSet(viewsets.ModelViewSet):
        serializer_class = FooSerializer
        queryset = Foo.objects.all()

Even though, in the above examples, things seem to be easy, the
management of such an application might be cumbersome if more entities
were introduced or the complexity of data representation of an entity
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

However, you are able to customize and extent the above behaviour and
add your own logic to your application. Specifically, APIMAS provides
two hooks for every action (before interacting with db and after) for
extending the logic of your application or executing arbitrary code
(e.g. executing a query or sending an email to an external agent).
You can do this as follows:

.. code-block:: python

    from apimas.modeling.adapters.drf.mixins import HookMixin

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

What we've got here is that we got the context of action, via
``self.unstash()`` method, then we computed the value of
``another_text`` using a method of (based on the logic of our
application), and finally, we told APIMAS (``self.stash()``) that
should add extra data to the model instance (another_text), apart from
that sent by client.
``self.unstash()`` returns a namedtuple with the following fields:

- ``instance``: Model instance to interact.
- ``data``: Dictionary of raw data, as sent by client.
- ``validated_data``: Dictionary of de-serialized, validated data.
- ``extra``: A dictionary with extra data, you wish to add to your
  model.
- ``response``: Response object.

Note that in some cases, there are some context fields that are not
initialized. For instance, in the ``preprocess_create()`` hook,
``instance`` is not initialized because model instance has not been
created yet.

The last part is to declare the use of the hook class. You have to
provide the ``hook_class`` parameter of the ``.drf_collection``
predicate.

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
be base classes of the generated serializer class, which are placed to
the lowest level of hierarchy. Therefore, in the above example, the
hierarchy of the generated class is as follows:

.. digraph:: foo
    
    node[shape=box];

    "BaseSerialzer" -> "MySerializer" -> "GeneratedSerializer";

Apparently, if you specify more than one classes on your
``model_serializers``, note that the left class is base of the right
class.

Further information about writable structure fields can be found in
the official documentation of django-rest-framework, 
`here <http://www.django-rest-framework.org/api-guide/relations/#writable-nested-serializers>`__.

Add more actions to your API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
You are able to specify which CRUD actions are allowed to be performed
on your collections. Currently, the declaration of additional actions
is not supported yet. Therefore, if you wish to add additional actions
to your API, for example:

.. code-block:: rest

    POST foo/1/myaction/

You need to write your own ViewSet class in which your extra action
will be included. For instance:

.. code-block:: python

    from rest_framework.decorators import detail_route
    from rest_framework.viewsets import GenericViewSet

    class MyViewSet(GenericViewSet):

        @detail_route(methods=['post'])
        def myaction(self, request, pk):
            # My code.
            ..

Similarly with the example of serializers, the final part is to define
the ``mixins`` parameter of your ``.drf_collection`` predicate, which
acts exactly the same, that is, your class will be base of the
generated class.

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

.. rubric::
    Note that the intuition of specifying the bases of the generated
    class, encourage the resusability of your code. For instance, you
    may have a custom ViewSet class which is shared amongst all your
    collections. Therefore, there is no need to write your own class
    for every class you want to customize, but instead, you simply
    declare the class you want to reuse on your specification.


django-rest-framework fields
----------------------------

By default, django-rest adapter tries to map a structural element,
pointed as ``.drf_field`` to field specified in your model, either as
an attribute or a function. However, it is not necessary to have 1 to
1 mapping between your API and storage configuration. For instance,
you may want to

- expose a field with different name as that specified in your model.
- define fields in your API which are not intended to be stored in
  your db.
- create structural responses.

Examples:

Define the name of source field explicitly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In this example, we expose a model field named ``text`` with different
name to the API, namely ``api_text``. For this purpose, we define the
parameter ``source`` of ``.drf_field`` predicate.


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

In this field, we add one more field (named "extra_field") to our
specification which is a string field and it does not have any storage
representation (parameter ``onmodel: False``, on ``.drf_field``).

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

Therefore, a server is aware of the existence of non-model fields, it
validates them, but it ignores them during write-operations
(obviously, because they are not part of the model). However, you are
able to handle them via the hooks APIMAS provides. In addition, by
default, when performing a read-operation such as list or retrieve,
the django-rest adapter will try to extract the value of such fields.
For this reason, if you want these fields to be readable, you must
provide the ``instance_source`` parameter on ``.drf_field`` predicate,
which is only applicable when ``onmodel`` has been set as False. This
parameter takes a function which must return the value of the field,
given ``instance`` as parameter.



.. code-block:: python
    :caption: mymodule.py

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

Create structural responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Apart from the things already mentioned, one additional reason for
having non-model fields is to serve responses in a structural way. For
instance, instead of returning the following response:

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

Apparently, your django-model is not aware of the node "data". Thus,
to make such a response, you format your specification as the one
below:

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

where node "data" is a non-model drf structural field, which consists
of model fields "api_text" and "number".

.. rubric::
    Warning: All fields which are stored to the db must be declared
    to a particular node. They must not be scattered around different
    nodes of specification.

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
On every permission rule, you have to specify the above information
which describe what are the prerequisites for a valid rule.

Example

.. code-block:: python

    rule = ('foo', 'create', 'admin', 'text', 'open', 'section 1.1')

The above rule indicates that an admin user (role) is authorized to
create (action) a new resource of `foo` type (collection) when the
state is `open`, and providing only the field `text` (field).
`section 1.1` is a comment made by the developer and it is ignored.

Now the developer decides that an admin user can also write one more
field e.g. `number`, on create operations.

This is done by setting one more rule, that is:

.. code-block:: python

    rule = ('foo', 'create', 'admin', 'text', 'open', 'section 1.1')
    rule2 = ('foo', 'create', 'admin', 'number', 'open', 'section 1.1')

or by creating pattern matches:

.. code-block:: python

    rule = ('foo', 'create', 'admin', 'text|number', 'open', 'section 1.1')

Supported APIMAS matches are:

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

You have to inform django-rest adapter which are the roles of the user
(authenticated entity that performs the request). The django-rest
adapter is informed about the user instance (in the context of
the request). However, it is unaware of how to extract the roles of
the user. For this reason, you have to create a property named
``apimas_roles`` on your user model (as specified in your django
settings). This property **must** return a list of strings.


.. code-block:: python

    class User(models.Model):
         ...

         @property
         def apimas_roles(self):
             ... 

Unauthenticated users
"""""""""""""""""""""

Unauthenticated parties are indicated with a role named **anonymous**.
This is particular useful, if your application does not have users.
Therefore, if you want a collection to be public, i.e.
unauthenticated users are able to consume it, then set something like
this:

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

An application may have a list of states which characterize a
particular entity. A common fact when having different states is that
different rules are applied or are valid for different states. For
example, a user can create or update a form when its status is 'open',
but they are not authorized to update the same form when its status is
'submitted'. Apparently, we can consider the previous statement as
a permission rule. The problem here is that the django-rest adapter
does not know about the existing states of an entity, and how a
specific state is considered as valid (because it depends on the
business logic of the application).

Therefore, to deal with this issue, an application with different
states for its entities has to specify some class methods, bound to
the model associated with the collection. These callables simply
check if a particular state is valid. Also, note that some actions
are performed on a particular resource (such as update, delete or
retrieve), while others on the set of resources, i.e. collection
(create or list). Hence, different callables must be triggered to
check the satisfiability of a state. These callables **must** have
the following signature:

.. code-block:: python

    @classmethod
    def check_collection_state_<state name>(cls, row, request, view):
        # your code. Return True or False.
        ...

    @classmethod
    def check_resource_state_<state name>(cls, obj, row, request, view):
        # your code. Return True or False.
        ...

Example, imagine you have the following permission rules:

.. code-block:: python

    rule = ('foo', 'update', 'anonymous', '*', 'open', 'section 1.1')
    rule2 = ('foo', 'update', 'anonymous', 'number', 'submitted', 'section 1.1')

In the above example, in the case of an update operation, the methods
listed below will be triggered to check if states 'open' or
'submitted' are satisfied:

- ``check_state_collection_open()``
- ``check_state_collection_submitted()``

If none of the states is valid, then an HTTP_403 error is returned. If
only one state is satisfied, then the django-rest adapter checks which
fields can be handled in this state, e.g. when the state is 'open', an
anonymous user can handle all fields, while when the state is
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

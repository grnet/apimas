Write APIMAS Specification
==========================

Before you read this section, you should take a look at the
introduction of APIMAS `specification <specification.html>`__.

Representing your application's REST API is an easy task.
First, you need to identify the collections of your application.
Consider a collection of resources named `foo`
and the following REST operations performed on it.

..
    XXX:
    - Support top-level resources
    - Should actions be listed within the
      .collection/.resource namespace?
      Do we need a separate .actions namespace?
    - Define list/delete for resources?
    - Why no .resource predicate?
    - Why not use namespace representation? It is shorter and cleaner.


.. code-block:: rest

    GET     /api/foo/
    GET     /api/foo/<pk>
    POST    /api/foo/
    PUT     /api/foo/<pk>
    PATCH   /api/foo/<pk>
    DELETE  /api/foo/<pk>

The above REST representation of your application is described by the
following specification document.

.. code-block:: python

    API_SPEC = {
        'api': {
            '.endpoint': {},
            'foo': {
                '.collection': {},
                '.actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {},
                }
            }
        }
    }

First of all, we specified ``.endpoint: {}`` which indicates that a set
of collections follows after a prefix `api/`.
`.collection: {}` specifies that `foo` is a collection.
`.actions` is a namespace predicate within which we define
which REST actions are to be performed on the collection.

Next, we need to define the underlying properties of the resources
that are included in this collection, i.e. their property schema.
This is defined within the node `'*'` as follows:


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

The above specification defines that the resources of collection
`foo` have the following two properties, `text` and `number` which are
of `string` and `integer` types respectively.
This process can be repeated for all the collections of your application
until you form the final specification. APIMAS provides a set of
predicates which are used and understood from all the applications
(which support APIMAS) to help you create your specification.
For the full reference,
see APIMAS standard `predicates <predicates.html>`__.

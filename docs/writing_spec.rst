Write APIMAS Specification
==========================

Before you read this section, you should take a look at the
introduction of APIMAS `specification <specification.html>`__.

Representing your application's REST API is an easy task. At the very
first stage, you should identify the collections of your application.
Consider we have one collection named `foo` and the following
REST operations performed on them.

.. code-block:: rest

    GET     /api/foo/
    GET     /api/foo/<pk>
    POST    /api/foo/
    PUT     /api/foo/<pk>
    PATCH   /api/foo/<pk>
    DELETE  /api/foo/<pk>

The above REST representation of your application is translated to the
following document.

.. code-block:: python

    API_SPEC = {
        'api': {
            '.endpoint': {},
            'foo': {
                '.collection': {},
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

First of all, we defined ``.endpoint: {}`` which indicates that a set
of collection is follows after `api/`. Node `foo` is characterized by
the predicates included in the node. Thus, `.collection: {}` predicate
denotes that `foo` is a `collection`. In addition, node includes the
structural element named `actions` which indicates which actions are
allowed to be performed on the collection.

What is missing is the underlying properties of the resources which
are included in this collection, i.e. their field schema.
This is defined inside the node `'*'` as follows:


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
`foo` have the following two properies, `text` and `number` which are
`string` and `integer` respectively. This process can be repeated for
all the collections of your application until you form the final
specification. APIMAS provides a set of predicates which are used and
understood from all the applications (which support APIMAS) to help
you create your specification. For the full reference of predicates,
see APIMAS standard `predicates <predicates.html>`__.

Example--APIMAS Specification
=============================

Before you read this section, you should take a look at the
APIMAS `specification <specification.html>`__ and
`predicates <predicates.html>`__.


Suppose that you want to build a simple e-shop application which
provide a REST API to its clients. A typical e-shop application
has the following entities which are described by some fields:

- ``users``: Users of the e-shop application which hold carts,
  make orders and buy products.
- ``products``: A list of products described with a product key,
  price, a name, a description and a quantity.
- ``carts``: Carts which contain a list of products.
- ``orders``: Orders made by users to purchase a specific cart.

Given the above, representing your application's REST API is an easy
task. First, you need to identify the collections of your application.

In this context of e-shop, consider the following collections of
resource corresponding to every entity, and the following actions
performed on them.

..
    XXX:
    - Support top-level resources
    - Should actions be listed within the
      .collection/.resource namespace?
      Do we need a separate .actions namespace?
    - Define list/delete for resources?
    - Why no .resource predicate?
    - Why not use namespace representation? It is shorter and cleaner.

``users``:

.. code-block:: rest

    POST   /api/users/
    GET    /api/users/<pk>/
    PUT    /api/users/<pk>/
    PATCH  /api/users/<pk>/

``products``:

.. code-block:: rest

    GET    /api/products/
    GET    /api/products/<pk>/

``carts``:

.. code-block:: rest

    POST   /api/carts/
    GET    /api/carts/
    GET    /api/carts/<pk>/
    PUT    /api/carts/<pk>/
    PATCH  /api/carts/<pk>/
    DELETE /api/carts/<pk>/

``orders``:

.. code-block:: rest

    POST   /api/orders/
    GET    /api/orders/
    GET    /api/orders/<pk>/

The above REST representation of your application is described by the
following specification document.

.. code-block:: python

    API_SPEC = {
        'api': {
            '.endpoint': {},
            'users': {
                '.collection': {},
                '.actions': {
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                }
            },
            'products': {
                '.collection': {},
                '.actions': {
                    '.list': {},
                    '.retrieve': {},
                }
            },
            'carts': {
                '.collection': {},
                '.actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {},
                }
            },
            'orders': {
                '.collection': {},
                '.actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                }
            }
        }
    }

First of all, we specified ``.endpoint: {}`` which indicates that a set
of collections follows after a prefix ``api/``.
``.collection: {}`` specifies that its parent node is a collection (
e.g. `users` is a collection). ``.actions`` is a namespace predicate within
which we define which REST actions are allowed to be performed on the
collection.

Next, we need to define the underlying properties of the resources
that are included in these collections i.e. their property schema.
This is defined within the node `'*'`. Let's begin with ``products``
collection as a reference. A product is described by a key, a name,
a description, a stock and a price. To expose this information to
the REST API, we define something like the following which indicates
that the aforementioned properties are `string`, `string`, `string`,
`integer` and `float` respectively.

.. code-block:: python

    'products': {
        '.collection': {},
        '*': {
            'key': {
                '.string': {'max_length': 10}
            },
            'name': {
                '.string': {},
            },
            'description': {
                '.string': {},
            },
            'stock': {
                '.integer': {},
            },
            'price': {
                '.float': {},
            },
        },
        '.actions': {
            '.list': {},
            '.retrieve': {},
        }
    }


This process can be repeated for all the collections of your
application until you form the final specification.
APIMAS provides a set of predicates which are used and
understood from all the applications (which support APIMAS)
to help you create your specification. Finally, we get
something like this:


.. code-block:: python

    API_SPEC = {
        'api': {
            '.endpoint': {},
            'users': {
                '.collection': {},
                '*': {
                    'id': {
                        '.serial': {},
                    },
                    'username': {
                        '.string': {},
                        '.required': {},
                    },
                    'first_name': {
                        '.string': {},
                        'required': {},
                    },
                    'last_name': {
                        '.string': {},
                        '.required': {},
                    },
                    'password': {
                        '.string': {},
                        '.required': {},
                        '.writeonly': {},
                    },
                    'email': {
                        '.email': {},
                        '.required': {},
                    },
                },
                '.actions': {
                    '.create': {},
                    '.update': {},
                    '.retrieve': {},
                }
            },
            'products': {
                '.collection': {},
                '*': {
                    'key': {
                        '.string': {'max_length': 10}
                    },
                    'name': {
                        '.string': {},
                    },
                    'description': {
                        '.string': {},
                    },
                    'stock': {
                        '.integer': {},
                    },
                    'price': {
                        '.float': {},
                    },
                },
                '.actions': {
                    '.list': {},
                    '.retrieve': {},
                }
            },
            'carts': {
                '.collection': {},
                '*': {
                    'customer': {
                        '.required': {},
                        '.ref': {'to': 'api/users'},
                    },
                    'ordered': {
                        '.boolean': {},
                        '.readonly': {},
                    },
                    'products': {
                        '.readonly': {},
                        '.structarray': {
                            'key': {
                                '.string': {},
                            },
                            'name': {
                                '.string': {},
                            },
                            'price': {
                                '.float': {},
                            },
                        }
                    },
                },
                '.actions': {
                    '.list': {},
                    '.retrieve': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {},
                },
            },
            'orders': {
                '.collection': {},
                '*': {
                    'id': {
                        '.serial': {},
                        '.readonly': {},
                    },
                    'address': {
                        '.required': {},
                        '.string': {},
                    },
                    'date': {
                        '.datetime': {'format': ['%Y-%m-%d %H:%M']},
                        '.required': {},
                    },
                    'cart': {
                        '.ref': {'to': 'api/carts'},
                        '.required': {},
                    }
                },
                '.actions': {
                    '.list': {},
                    '.create': {},
                    '.update': {},
                    '.delete': {},
                    '.retrieve': {},
                }
            },
        }
    }


.. note::
  ``cart`` field of collection ``orders`` points to a resource of
  another collection, i.e. ``carts`` as specified in the `'api/carts'`
  location of specification.


.. seealso::
    For the full reference,
    see APIMAS `predicates <predicates.html>`__.

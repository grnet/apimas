APIMAS standard predicates
==========================

As explained in the previous `section <specification.html>`__,
an APIMAS specification contains structural elements with their respective
metadata. This metadata are prefixed with a dot '.' and called `Predicates`.
Predicates add semantics to their parent structural elements and therefore,
it is a way to change the behaviour of your application.

APIMAS defines a set of predicates whose semantics are understood from
every application (both client and server side) and help you create
your specification. Below, there is a list of the widely-known
predicates:

Structural predicates
---------------------

The predicates listed below describe basic structural elements of your REST
application.


================= =================================================================
Predicate         Description
================= =================================================================
``.endpoint``     It defines a location to the web after which there is a set of
                  collections to interact.
``.collection``   It defines that the parent node is a collection of resources of the
                  same type, where each resource can be related to other resources,
                  it is described by some data, and there are actions that can be
                  performed on it.
================= =================================================================


Action predicates
-----------------

There are also predicates which delineate what actions or methods can be
performed on a collection or a resource individually.

================= =================================================================
Predicate         Description
================= =================================================================
``.list``         The list of resources contained to the collection is permitted.
                  It corresponds to:

                  GET <collection name>/
``.retrieve``     A single resource can be retrieved and viewed. It corresponds to:
                  
                  GET <collection name>/<pk>/
``.create``       A new resource of the type defined by the collection can be created.
                  It corresponds to:

                  POST <collection name>/

``.update``       A single resource can be updated. It corresponds to:

                  PUT    <collection name>/<pk>/
                  PATCH  <collection name>/<pk>/

                  **Note**: The ``.update`` predicate allows a single resource
                  to be both replaced and partially updated.

``.delete``       A single resource can be deleted from the set of existing.
                  It corresponds to:

                  DELETE <collection name>/<pk>/
================= =================================================================

Action predicates are specified inside the structural element **actions** of
a collection definition.

Example:

.. code-block:: python

    {
        'foo': {
            '.collection': {},
            'actions': {
                '.list': {},
                '.retrieve': {},
            }
        }
    }

In the above example, only retrieve and list operations are permitted for
collection 'foo'.


Resource description
--------------------

Each resource contained in a particular collection is described by a field
schema with properties and data associated with it. Specifically, each
resource is described by a set of fields with specific type and behaviour.

Similarly to the structural and action predicate, there are also predicates
to describe the properties of every field. These predicates slit into two
categories: **a)**: types, **b)**: properties.


Type Predicates
^^^^^^^^^^^^^^^

================= =================================================================
Predicate         Description
================= =================================================================
``.integer``      Parent node is an integer.
``.float``        Parent node is a floating point number.
``.string``       Parent node is a string. Small to middle sized strings are
                  supported.

                  **Parameters**:
                      `maxlength`: The upper bound of string's size (optional).
                      The default is 255.
``.text``         Parent node is a text.
``.boolean``      Parent node is either true or false.
``.email``        Parent node is an email address.
``.serial``       Parent node is a serial, non-writable integer number.
``.choices``      Parent node can take a list of allowed values as specified
                  by the parameter ``allowed``.

                      .. code-block:: python

                          'foo': {
                              '.choices': {
                                  'allowed': [1, 'bar']
                              }
                          }
                      Parent node can be either 1 or 'bar'.

                  **Parameters**:
                      `allowed`: A list of acceptable values for the parent.

                      `display`: A list  of the displayed values of the node.

``.ref``          Parent node points to the web location of another resource.

                  **Parameters**:
                      `to`:   Name of the collection where resource is located.
                              This must be a valid name of a collection which
                              have been specified on APIMAS specification too.
                      `many`: true if parent node points to multiple resources,
                              false otherwise.
``.identity``     Parent node points to the web location of this resource.
                  It's actually the REST identifier of the resource. It is
                  non-writable.
``.file``         Parent node is a file.
``.date``         Parent node is a date, represented by a string.
                  
                   
                  **Parameters**:
                      `format`:  A list of string representing the allowed
                      input formats of the date. (optional).
                      By default only `ISO-8601 <http://www.iso.org/iso/home/standards/iso8601.htm>`__
                      is allowed.
``.datetime``     Parent node is a datetime, represented by a string.

                  **Parameters**:
                      `format`:  A list of strings representing the allowed.
                      input formats of the datetime.
                      By default only `ISO-8601 <http://www.iso.org/iso/home/standards/iso8601.htm>`__
                      is allowed.
``.struct``       Parent node is a structure which consists of another field
                  schema, i.e. a set of fields with their types and properties.

                  **Arguments**:
                      A document-like representation with the name of fields as
                      key and their description as defined by the use of predicates.

``.structarray``  Parent node is an array of structures.

                  **Arguments**:
                      A document-like representation with the name of fields as
                      key and their description as defined by the use of predicates.
================= =================================================================

.. note::

    Every field **must** be described with at most one type.

Properties predicates
^^^^^^^^^^^^^^^^^^^^^

Properties predicates, typically, describe the behaviour and how can be used
on the various actions.

================= =================================================================
Predicate         Description
================= =================================================================
``.required``     The parent node is required and **must** be included in every
                  API call associated with create and update operations
                  (POST and PUT requests).
``.readonly``     The parent node is read-only and its value can be viewed, but
                  it cannot be modified or set.
``.writeonly``    The parent node is write-only and its value can be modified
                  or set, but it cannot be viewed.
``.nullable``     The parent node can have null values.
================= =================================================================

.. note::

    Some predicates are mutually exclusive. Specifically a
    node cannot be described as both ``.readonly`` and ``writeonly``
    or ``.required`` and ``.readonly``.

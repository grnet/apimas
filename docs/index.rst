.. APIMAS documentation master file


APIMAS - API Modeling and Serving
*********************************

APIMAS provides a flexible way for building, modifying and
extending your application without the cumbersome management
due to the complexity and the size of it.

Trying it out
=============

apimas
------

Explore apimas package to find out how to model your REST API, and
build and deploy your application.


First, create a `virtualenv <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`__:

.. code-block:: console

    virtualenv virtualenv-apimas
    source virtualenv-apimas/bin/activate

then, install apimas via `pip <https://pip.pypa.io/en/stable/>`__:

.. code-block:: console

    pip install apimas

apimas-drf
----------

For apimas support for building django applications,
you should checkout apimas-drf package. 

In a virtualenv run:

.. code-block:: console

    pip install apimas-drf


Contents
========

.. toctree::
   :maxdepth: 4


   overview
   specification
   predicates
   writing_spec
   drf_adapter
   clients
   license

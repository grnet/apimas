.. APIMAS documentation master file


APIMAS - API Modeling and Serving
*********************************

Install
=======
As a starting point, create a `virtualenv <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`__:

.. code-block:: shell

    virtualenv virtualenv-apimas
    source virtualenv-apimas/bin/activate


Now, you can easily install apimas via ``pip``. Run the following
command:

.. code-block:: shell

    pip install apimas

Alternatively, install apimas from github repository:

.. code-block:: shell

    git clone https://github.com/grnet/apimas
    cd apimas/apimas
    python setup.py install


Contents
========

.. toctree::
   :maxdepth: 2


   basic_architecture
   specification
   writing_spec
   predicates
   drf_adapter
   clients
   license

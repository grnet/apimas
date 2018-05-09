API Modeling and Serving
========================

apimas provides an intuitive way to build scalable REST APIs and
serve an application. The goal of apimas is to provide a flexible
way for building, modifying and extending your application without
the cumbersome management due to the complexity and the size of it.

Three packages are provided:

* apimas: Basic mechanism and backend-independent tools

* apimas-django: Support for building Django applications

* docular: Tool to handle recursive object-documents


Installation
------------

Install from pypi using:

```
pip install docular apimas apimas-django
```

Alternatively, to install from the repository, issue:

```
python setup.py install
```

in all package subdirectories.


Documentation
-------------
Please see the [APIMAS documentation](http://apimas.readthedocs.io/en/latest/index.html)
for information on using APIMAS.

Note: Documentation is not up-to-date. For a concrete working example of a
django application using apimas, see under apimas-django/examples/.


Copyright and license
---------------------

Copyright (C) 2016-2018 GRNET S.A.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
sys.path.append('..')
from setup_common import setup_package


EXTRA_KWARGS = {
    'namespace_packages': ['apimas'],
}
DESCRIPTION = 'APIMAS support for django-rest-framework applications'
setup_package(description=DESCRIPTION,
              excluded=['examples', 'tests'], **EXTRA_KWARGS)

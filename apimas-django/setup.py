import sys
sys.path.append('..')
from setup_common import setup_package


EXTRA_KWARGS = {
    'namespace_packages': ['apimas'],
}
setup_package(description='APIMAS support for django applications',
              excluded=['examples', 'tests'], **EXTRA_KWARGS)

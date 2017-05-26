import sys
sys.path.append('..')
from setup_common import setup_package


EXTRA_KWARGS = {
    'entry_points': {
        'console_scripts': {
            'apimas=apimas.cmd:main'
        }
    },
    'scripts': ['auto/builder/docker/home/bin/mkdeb'],
}

setup_package(description='API Modeling and Serving', **EXTRA_KWARGS)

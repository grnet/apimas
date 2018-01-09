import os
from setuptools import setup, find_packages

CURPATH = os.path.dirname(os.path.realpath(__file__))


def get_package_info():
    version_file = os.path.join(CURPATH, "version.txt")
    with open(version_file) as f:
        return (x.strip() for x in f.read().strip().split())


def get_requirements():
    req_file = os.path.join(CURPATH, "requirements.txt")
    with open(req_file) as f:
        return [
            x.strip('\n')
            for x in f.readlines()
            if x and x[0] != '#'
        ]


def setup_package(description='', excluded=None, **kwargs):
    package_name, version = get_package_info()
    requirements = get_requirements()
    standard_kwargs = {
        'name': package_name,
        'version': version,
        'license': 'Affero GPL v3',
        'author': 'GRNET S.A.',
        'author_email': 'apimas@dev.grnet.gr',
        'description': description,
        'packages': find_packages(exclude=excluded or []),
        'install_requires': requirements,
    }
    kwargs = dict(standard_kwargs, **kwargs)
    setup(**kwargs)


EXTRA_KWARGS = {
    'entry_points': {
        'console_scripts': {
            'apimas=apimas.cmd:main'
        }
    },
    'scripts': ['auto/builder/docker/home/bin/mkdeb'],
}

setup_package(description='API Modeling and Serving', **EXTRA_KWARGS)

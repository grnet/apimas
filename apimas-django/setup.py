import os
from setuptools import setup, find_packages

CURPATH = os.path.dirname(os.path.realpath(__file__))


def get_version():
    version_file = os.path.join(CURPATH, "version.txt")
    with open(version_file) as f:
        info = [x.strip() for x in f.read().strip().split()]
        return info[1]


def get_requirements():
    req_file = os.path.join(CURPATH, "requirements.txt")
    with open(req_file) as f:
        return [
            x.strip('\n')
            for x in f.readlines()
            if x and x[0] != '#'
        ]

package_name = 'apimas-django'
description = 'APIMAS support for django applications'
version = get_version()
requirements = get_requirements()
requirements.append('apimas==%s' % version)

setup(
    name=package_name,
    version=version,
    license='Affero GPL v3',
    author='GRNET S.A.',
    author_email='team@dev.grnet.gr',
    description=description,
    packages=find_packages(exclude=['examples', 'tests']),
    install_requires=requirements
)

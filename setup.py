from setuptools import setup, find_packages
import os

with open("version.txt") as f:
    PACKAGE_NAME, VERSION = \
        (x.strip() for x in f.read().strip().split())

COMPATIBLE_VERSION = '.'.join(VERSION.split('.')[:2])

with open('requirements.txt') as f:
    INSTALL_REQUIRES = [
        x.strip('\n')
        for x in f.readlines()
        if x and x[0] != '#'
    ]

setup(
    name=PACKAGE_NAME,
    version=VERSION,
    license='Affero GPL v3',
    author='GRNET S.A.',
    author_email='apimas@dev.grnet.gr',
    description='API Modeling And Serving',
    packages=find_packages(exclude=['examples']),
    install_requires=INSTALL_REQUIRES,
    entry_points={
        'console_scripts': {
            'apimas=apimas.modeling.cli.cli:main'
        }
    },
    scripts=['scripts/apimas-mkdeb'],
)

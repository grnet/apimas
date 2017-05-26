from setuptools import setup, find_packages


def get_package_info():
    with open("version.txt") as f:
        return (x.strip() for x in f.read().strip().split())


def get_requirements():
    with open('requirements.txt') as f:
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

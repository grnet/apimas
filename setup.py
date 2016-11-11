from apimas import VERSION
from setuptools import setup, find_packages

setup(
    name='apimas',
    version=VERSION,
    description='API Modeling And Serving',
    packages=find_packages(exclude=['examples']),
    install_requires=[],
    entry_points={
        'console_scripts': {
            'apimas=apimas.modeling.cli.cli:main'
        }
    }
)

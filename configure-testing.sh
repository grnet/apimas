cd "$(dirname "$0")"
ROOT=$(pwd)

cd docular && python setup.py install && cd ..
cd apimas && python setup.py install && cd ..
cd apimas-django && python setup.py install && pip install -r requirements_dev.txt && cd ..

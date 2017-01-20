import os
import random
import string

import pytest

from s3pypi.package import Package


@pytest.fixture(scope='function')
def secret():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(24))


@pytest.fixture(scope='function', params=['helloworld-0.1', 's3pypi-0.1.3'])
def sdist_output(request):
    with open(os.path.join('tests', 'data', 'sdist_output', request.param)) as f:
        yield f.read(), request.param


@pytest.fixture(scope='function', params=[
    ('s3pypi', {Package('s3pypi-' + v, {'s3pypi-%s.tar.gz' % v, 's3pypi-%s-py2-none-any.whl' % v})
                for v in ('0.1.1', '0.1.2')})
])
def index_html(request):
    name, packages = request.param
    with open(os.path.join('tests', 'data', 'index', name + '.html')) as f:
        yield f.read().strip(), packages

import os
import random
import string

import pytest


@pytest.fixture(scope='function')
def secret():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(24))


@pytest.fixture(scope='function', params=['helloworld-0.1', 's3pypi-0.1.3'])
def sdist_output(request):
    with open(os.path.join('tests', 'data', 'sdist', request.param)) as f:
        yield f.read(), request.param

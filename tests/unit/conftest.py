import os
import random
import string

import pytest

from s3pypi.package import Package


@pytest.fixture(scope="function")
def secret():
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(24)
    )


@pytest.fixture(scope="function")
def private():
    return True


@pytest.fixture(
    scope="function",
    params=["helloworld-0.1", "s3pypi-0.1.3", "distribution_costs-0.1.0"],
)
def sdist_output(request):
    with open(os.path.join("tests", "data", "sdist_output", request.param)) as f:
        yield f.read(), request.param


@pytest.fixture(scope="function", params=["distribution_costs-0.1.0"])
def bdist_wheel_output(request):
    with open(os.path.join("tests", "data", "sdist_output", request.param)) as f:
        yield f.read(), "dist/{}-py3-none-any.whl".format(request.param)

@pytest.fixture(scope="function", params=["hello-world-0.1.0"])
def wheel_metadata(request):
    with open(os.path.join("tests", "data", "wheel_metadata", request.param)) as f:
        yield f.read(), request.param

@pytest.fixture(
    scope="function",
    params=[
        (
            "s3pypi",
            {
                Package(
                    "s3pypi-" + v,
                    {"s3pypi-%s.tar.gz" % v, "s3pypi-%s-py2-none-any.whl" % v},
                )
                for v in (
                    "0",
                    "0!0",
                    "0+local",
                    "0.0",
                    "0.1.1",
                    "0.1.2",
                    "0.dev0",
                    "0.post0",
                    "0a0",
                    "0rc0",
                )
            },
        )
    ],
)
def index_html(request):
    name, packages = request.param
    with open(os.path.join("tests", "data", "index", name + ".html")) as f:
        yield f.read().strip(), packages

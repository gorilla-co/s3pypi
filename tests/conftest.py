from pathlib import Path

import pytest

from s3pypi.index import Package


@pytest.fixture(scope="session")
def data_dir():
    return Path(__file__).parent.resolve() / "data"


@pytest.fixture(
    scope="function",
    params=[
        (
            "s3pypi",
            {
                Package(
                    "s3pypi",
                    v,
                    {
                        Path(f"s3pypi-{v}.tar.gz"),
                        Path(f"s3pypi-{v}-py2-none-any.whl"),
                    },
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
def index_html(request, data_dir):
    name, packages = request.param
    with open(data_dir / "index" / f"{name}.html") as f:
        yield f.read().strip(), packages

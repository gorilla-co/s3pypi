import pytest

from s3pypi import core


@pytest.fixture(scope="session", params=[("hello-world", "0.1.0")])
def wheel_metadata(request, data_dir):
    name, version = request.param
    with open(data_dir / "wheel_metadata" / f"{name}-{version}") as f:
        yield f.read(), request.param


def test_find_name_from_wheel_metadata(wheel_metadata):
    metadata, expected_name_version = wheel_metadata
    name, version = core.find_wheel_name_and_version(metadata)
    assert name, version == expected_name_version

from pathlib import Path

import pytest

from s3pypi import core


@pytest.mark.parametrize(
    "name, normalized",
    [
        ("company.test", "company-test"),
        ("company---test.1", "company-test-1"),
        ("company___test.2", "company-test-2"),
    ],
)
def test_normalize_package_name(name, normalized):
    assert core.normalize_package_name(name) == normalized


@pytest.mark.parametrize(
    "dist",
    [
        core.Distribution(
            name="hello-world",
            version="0.1.0",
            local_path=Path("dist/hello-world-0.1.0.tar.gz"),
        ),
        core.Distribution(
            name="foo-bar",
            version="1.2.3",
            local_path=Path("dist/foo-bar-1.2.3.zip"),
        ),
    ],
)
def test_parse_distribution(dist):
    path = dist.local_path
    assert core.parse_distribution(path) == dist

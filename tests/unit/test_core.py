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
    "filename, dist",
    [
        ("hello_world-0.1.0.tar.gz", core.DistributionId("hello_world", "0.1.0")),
        ("foo_bar-1.2.3-py3-none-any.whl", core.DistributionId("foo_bar", "1.2.3")),
    ],
)
def test_parse_distribution_id(filename, dist):
    assert core.parse_distribution_id(filename) == dist

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

import pytest

from s3pypi.index import Index
from s3pypi.storage import S3Storage


@pytest.mark.parametrize(
    "package_name, directory",
    [
        ("company.test", "company-test"),
        ("company---test.1", "company-test-1"),
        ("company___test.2", "company-test-2"),
    ],
)
def test_directory_normalize_package_name(package_name, directory):
    assert S3Storage.directory(package_name) == directory


def test_index_storage_roundtrip(s3_bucket):
    directory = "foo"
    index = Index({"bar"})

    storage = S3Storage(s3_bucket.name)
    storage.put_index(directory, index)
    got = storage.get_index(directory)

    assert got == index


def test_prefix_in_s3_key():
    prefix = "1234567890"

    storage = S3Storage(bucket="example", prefix=prefix)
    obj = storage._object(directory="foo", filename="bar")

    assert obj.key.startswith(prefix + "/")

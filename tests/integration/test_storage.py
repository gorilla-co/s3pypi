from s3pypi.index import Index
from s3pypi.storage import S3Storage


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

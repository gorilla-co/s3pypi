from s3pypi.index import Filename, Index
from s3pypi.storage import S3Storage


def test_index_storage_roundtrip(boto3_session, s3_bucket):
    directory = "foo"
    index = Index({"bar": Filename("bar")})

    storage = S3Storage(boto3_session, s3_bucket.name)
    storage.put_index(directory, index)
    got = storage.get_index(directory)

    assert got == index


def test_prefix_in_s3_key(boto3_session):
    prefix = "1234567890"

    storage = S3Storage(boto3_session, bucket="example", prefix=prefix)
    obj = storage._object(directory="foo", filename="bar")

    assert obj.key.startswith(prefix + "/")

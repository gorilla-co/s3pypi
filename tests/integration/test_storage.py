from s3pypi.index import Index
from s3pypi.storage import S3Config, S3Storage


def test_index_storage_roundtrip(boto3_session, s3_bucket):
    directory = "foo"
    index = Index({"bar": None})

    cfg = S3Config(bucket=s3_bucket.name)
    storage = S3Storage(boto3_session, cfg)

    storage.put_index(directory, index)
    got = storage.get_index(directory)

    assert got == index


def test_prefix_in_s3_key(boto3_session):
    cfg = S3Config(bucket="example", prefix="1234567890")
    storage = S3Storage(boto3_session, cfg)

    obj = storage._object(directory="foo", filename="bar")

    assert obj.key.startswith(cfg.prefix + "/")

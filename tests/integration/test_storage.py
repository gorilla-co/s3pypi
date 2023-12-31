import pytest

from s3pypi.index import Index
from s3pypi.storage import S3Config, S3Storage


def test_index_storage_roundtrip(boto3_session, s3_bucket):
    directory = "foo"
    index = Index({"bar": None})

    cfg = S3Config(bucket=s3_bucket.name)
    s = S3Storage(boto3_session, cfg)

    s.put_index(directory, index)
    got = s.get_index(directory)

    assert got == index


index = object()


@pytest.mark.parametrize(
    "cfg, directory, filename, expected_key",
    [
        (S3Config(""), "/", index, "index.html"),
        (S3Config(""), "foo", "bar", "foo/bar"),
        (S3Config("", prefix="P"), "/", index, "P/"),
        (S3Config("", prefix="P"), "foo", "bar", "P/foo/bar"),
        (S3Config("", prefix="P", unsafe_s3_website=True), "/", index, "P/index.html"),
        (S3Config("", unsafe_s3_website=True), "/", index, "index.html"),
    ],
)
def test_s3_key(boto3_session, cfg, directory, filename, expected_key):
    s = S3Storage(boto3_session, cfg)
    if filename is index:
        filename = s.index_name

    obj = s._object(directory, filename)

    assert obj.key == expected_key


def test_list_dirs(boto3_session, s3_bucket):
    cfg = S3Config(bucket=s3_bucket.name, prefix="AA")
    s = S3Storage(boto3_session, cfg)
    s.put_index("one", Index())
    s.put_index("two", Index())
    s.put_index("three", Index())

    assert s._list_dirs() == ["one/", "three/", "two/"]

    cfg = S3Config(bucket=s3_bucket.name, prefix="BBBB")
    s = S3Storage(boto3_session, cfg)
    s.put_index("xxx", Index())
    s.put_index("yyy", Index())

    assert s._list_dirs() == ["xxx/", "yyy/"]

    cfg = S3Config(bucket=s3_bucket.name)
    s = S3Storage(boto3_session, cfg)

    assert s._list_dirs() == ["AA/", "BBBB/"]

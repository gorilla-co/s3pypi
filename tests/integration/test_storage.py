from unittest import mock

import pytest
from botocore.exceptions import ClientError

from s3pypi.index import Index
from s3pypi.storage import S3Config, S3Storage


def test_index_storage_roundtrip(s3_bucket):
    directory = "foo"
    index = Index({"bar": None})

    cfg = S3Config(bucket=s3_bucket.name)
    s = S3Storage(cfg)

    s.put_index(directory, index)
    got = s.get_index(directory)

    assert got == index


def test_get_missing_index(s3_bucket):
    s = S3Storage(S3Config(bucket=s3_bucket.name))

    assert s.get_index("foo") == Index()


def test_get_index_propagates_other_errors(s3_bucket, monkeypatch):
    s = S3Storage(S3Config(bucket=s3_bucket.name))
    error = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
    obj = mock.Mock(**{"get.side_effect": error})
    monkeypatch.setattr(s, "_object", lambda *_: obj)

    with pytest.raises(ClientError, match="AccessDenied"):
        s.get_index("foo")


index = object()


@pytest.mark.parametrize(
    "cfg, directory, filename, expected_key",
    [
        (S3Config(""), "/", index, "index.html"),
        (S3Config(""), "foo", "bar", "foo/bar"),
        (S3Config("", prefix="P"), "/", index, "P/"),
        (S3Config("", prefix="P"), "foo", "bar", "P/foo/bar"),
        (S3Config("", prefix="P", index_html=True), "/", index, "P/index.html"),
        (S3Config("", index_html=True), "/", index, "index.html"),
    ],
)
def test_s3_key(cfg, directory, filename, expected_key):
    s = S3Storage(cfg)
    if filename is index:
        filename = s.index_name

    obj = s._object(directory, filename)

    assert obj.key == expected_key


def test_list_directories(s3_bucket):
    cfg = S3Config(bucket=s3_bucket.name, prefix="AA")
    s = S3Storage(cfg)
    s.put_index("one", Index())
    s.put_index("two", Index())
    s.put_index("three", Index())

    assert s.list_directories() == ["one/", "three/", "two/"]

    cfg = S3Config(bucket=s3_bucket.name, prefix="BBBB")
    s = S3Storage(cfg)
    s.put_index("xxx", Index())
    s.put_index("yyy", Index())

    assert s.list_directories() == ["xxx/", "yyy/"]

    cfg = S3Config(bucket=s3_bucket.name)
    s = S3Storage(cfg)

    assert s.list_directories() == ["AA/", "BBBB/"]

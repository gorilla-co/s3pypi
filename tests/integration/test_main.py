import glob

import pytest

from s3pypi.__main__ import main as s3pypi, string_dict


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "ServerSideEncryption=aws:kms,SSEKMSKeyId=1234...,  foo=bar",
            dict(ServerSideEncryption="aws:kms", SSEKMSKeyId="1234...", foo="bar"),
        )
    ],
)
def test_string_dict(text, expected):
    assert string_dict(text) == expected


def test_main_upload_package(chdir, data_dir, s3_bucket):
    with chdir(data_dir):
        dist = sorted(glob.glob("dists/*"))
        s3pypi(*dist, "--bucket", s3_bucket.name)

    def read(key: str) -> bytes:
        return s3_bucket.Object(key).get()["Body"].read()

    def assert_pkg_exists(prefix: str, filename: str):
        assert read(prefix + filename)
        assert f">{filename}</a>" in read(prefix).decode()

    assert_pkg_exists("foo/", "foo-0.1.0.tar.gz")
    assert_pkg_exists("hello-world/", "hello_world-0.1.0-py3-none-any.whl")

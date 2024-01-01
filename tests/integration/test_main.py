import logging

import pytest

from s3pypi import __prog__
from s3pypi.__main__ import main as s3pypi, string_dict
from s3pypi.index import Hash, Index


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


@pytest.mark.parametrize("prefix", ["", "packages", "packages/abc"])
def test_main_upload_package(chdir, data_dir, s3_bucket, dynamodb_table, prefix):
    args = ["dists/*", "--bucket", s3_bucket.name, "--put-root-index"]
    if prefix:
        args.extend(["--prefix", prefix])

    with chdir(data_dir):
        s3pypi("upload", *args)

    def read(key: str) -> bytes:
        return s3_bucket.Object(key).get()["Body"].read()

    root_index = read(f"{prefix}/" if prefix else "index.html").decode()

    def assert_pkg_exists(pkg: str, filename: str):
        path = (f"{prefix}/" if prefix else "") + f"{pkg}/"
        assert read(path + filename)
        assert f">{filename}</a>" in read(path).decode()
        assert f">{pkg}</a>" in root_index

    assert_pkg_exists("foo", "foo-0.1.0.tar.gz")
    assert_pkg_exists("hello-world", "hello_world-0.1.0-py3-none-any.whl")
    assert_pkg_exists("xyz", "xyz-0.1.0.zip")


def test_main_upload_package_exists(chdir, data_dir, s3_bucket, caplog):
    dist = "dists/foo-0.1.0.tar.gz"

    with chdir(data_dir):
        s3pypi("upload", dist, "--bucket", s3_bucket.name)
        s3pypi("upload", dist, "--bucket", s3_bucket.name)

        with pytest.raises(SystemExit, match="ERROR: Found 1 existing files on S3"):
            s3pypi("upload", dist, "--strict", "--bucket", s3_bucket.name)

        s3pypi("upload", dist, "--force", "--bucket", s3_bucket.name)

    msg = "foo-0.1.0.tar.gz already exists! (use --force to overwrite)"
    success = (__prog__, logging.INFO, "Uploading " + dist)
    warning = (__prog__, logging.WARNING, msg)

    assert caplog.record_tuples == [success, warning, warning, success]


@pytest.mark.parametrize(
    ["dists", "error_msg"],
    [
        (["dists"], r"Not a file: dists"),
        (["dists/invalid.whl"], r"No valid files found matching: dists/invalid\.whl"),
        (
            ["dists/foo-0.1.0.tar.gz", "dists/*.invalid"],
            r"No valid files found matching: dists/\*\.invalid",
        ),
    ],
)
def test_main_upload_package_invalid(
    dists, error_msg, chdir, data_dir, s3_bucket, caplog
):
    with chdir(data_dir):
        with pytest.raises(SystemExit, match=f"ERROR: {error_msg}"):
            s3pypi("upload", *dists, "--bucket", s3_bucket.name)


def test_main_upload_package_with_force_updates_hash(chdir, data_dir, s3_bucket):
    with open(data_dir / "index" / "hello_world.html", "rb") as index_file:
        s3_bucket.Object("hello-world/").put(Body=index_file)

    def get_index():
        html = s3_bucket.Object("hello-world/").get()["Body"].read()
        return Index.parse(html.decode())

    assert get_index().filenames == {
        "hello-world-0.1.0.tar.gz": None,
        "hello_world-0.1.0-py3-none-any.whl": None,
    }

    with chdir(data_dir):
        dist = "dists/hello_world-0.1.0-py3-none-any.whl"
        s3pypi("upload", dist, "--force", "--bucket", s3_bucket.name)

    assert get_index().filenames == {
        "hello-world-0.1.0.tar.gz": None,
        "hello_world-0.1.0-py3-none-any.whl": Hash(
            "sha256", "c5a2633aecf5adc5ae49b868e12faf01f2199b914d4296399b52dec62cb70fb3"
        ),
    }


def test_main_delete_package(chdir, data_dir, s3_bucket):
    with chdir(data_dir):
        s3pypi("upload", "dists/*", "--bucket", s3_bucket.name, "--put-root-index")
        s3pypi("delete", "hello-world", "0.1.0", "--bucket", s3_bucket.name)

    def read(key: str) -> bytes:
        return s3_bucket.Object(key).get()["Body"].read()

    root_index = read("index.html").decode()

    def assert_pkg_exists(pkg: str, filename: str):
        path = f"{pkg}/"
        assert read(path + filename)
        assert f">{filename}</a>" in read(path).decode()
        assert f">{pkg}</a>" in root_index

    for deleted_key in [
        "hello-world/",
        "hello-world/hello_world-0.1.0-py3-none-any.whl",
    ]:
        with pytest.raises(s3_bucket.meta.client.exceptions.NoSuchKey):
            s3_bucket.Object(deleted_key).get()

    assert ">hello-world</a>" not in root_index
    assert_pkg_exists("foo", "foo-0.1.0.tar.gz")
    assert_pkg_exists("xyz", "xyz-0.1.0.zip")

import sys

from s3pypi.__main__ import main as s3pypi


def test_main_create_and_upload_package(project_dir, s3_bucket):
    with project_dir("hello-world"):
        s3pypi("--bucket", s3_bucket.name)

    assert s3_bucket.Object("hello-world/index.html").get()
    assert s3_bucket.Object("hello-world/hello-world-0.1.0.tar.gz").get()
    assert s3_bucket.Object(
        "hello-world/hello_world-0.1.0-py{}-none-any.whl".format(sys.version_info.major)
    ).get()


def test_main_upload_sdist_package_from_custom_dist_path(project_dir, s3_bucket):
    with project_dir("custom-dist-path"):
        s3pypi("--dist-path", "my-dist", "--bucket", s3_bucket.name)

    assert s3_bucket.Object("foo/index.html").get()
    assert s3_bucket.Object("foo/foo-0.1.0.tar.gz").get()


def test_main_upload_wheel_package_from_custom_dist_path(project_dir, s3_bucket):
    with project_dir("custom-dist-path"):
        s3pypi("--dist-path", "helloworld-dist", "--bucket", s3_bucket.name)

    assert s3_bucket.Object("hello-world/index.html").get()
    assert s3_bucket.Object(
        "hello-world/hello_world-0.1.0-py{}-none-any.whl".format(sys.version_info.major)
    ).get()

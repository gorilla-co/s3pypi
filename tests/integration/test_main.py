from s3pypi.__main__ import main as s3pypi


def test_main_create_and_upload_package(project_dir, s3_bucket):
    with project_dir("hello-world"):
        s3pypi("--bucket", s3_bucket.name)

    assert s3_bucket.Object("hello-world/index.html").get()
    assert s3_bucket.Object("hello-world/hello-world-0.1.0.tar.gz").get()
    assert s3_bucket.Object("hello-world/hello_world-0.1.0-py3-none-any.whl").get()

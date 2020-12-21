import glob

from s3pypi.__main__ import main as s3pypi


def test_main_upload_package(chdir, data_dir, s3_bucket):
    with chdir(data_dir):
        dist = sorted(glob.glob("dists/*"))
        s3pypi(*dist, "--bucket", s3_bucket.name)

    assert s3_bucket.Object("foo/").get()
    assert s3_bucket.Object("foo/foo-0.1.0.tar.gz").get()
    assert s3_bucket.Object("hello-world/").get()
    assert s3_bucket.Object("hello-world/hello_world-0.1.0-py3-none-any.whl").get()

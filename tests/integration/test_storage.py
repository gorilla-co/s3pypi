from pathlib import Path

from s3pypi.index import Index, Package
from s3pypi.storage import S3Storage

package = Package("test", "0.1.0", {Path("test-0.1.0.tar.gz")})


def test_index_storage_roundtrip(s3_bucket):
    index = Index({package})

    storage = S3Storage(s3_bucket.name)
    storage.put_index(index)
    got = storage.get_index(package)

    assert got == index


def test_secret_in_s3_key():
    secret = "1234567890"

    storage = S3Storage("example", prefix=secret)
    obj = storage._object(package, filename="")

    assert obj.key.startswith(secret + "/")

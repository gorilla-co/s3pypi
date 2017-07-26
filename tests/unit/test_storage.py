from s3pypi.package import Package
from s3pypi.storage import S3Storage


def test_secret_in_s3_key(secret):
    storage = S3Storage('appstrakt-pypi', secret)
    package = Package('test-0.1.0', [])
    assert secret in storage._object(package, 'index.html').key
    assert storage.acl == 'public-read'


def test_private_s3_key(private):
    storage = S3Storage('appstrakt-pypi', private=private)
    assert storage.acl == 'private'

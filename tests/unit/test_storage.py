from s3pypi.storage import S3Storage


def test_secret():
    storage = S3Storage('appstrakt-pypi', 'secret')
    assert 'secret' in storage.url

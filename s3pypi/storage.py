import os

import boto
from boto.exception import S3ResponseError
from boto.s3.key import Key

from s3pypi.package import Index

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


class S3Storage(object):
    """Abstraction for storing package archives and index files in an S3 bucket."""

    def __init__(self, bucket, secret=None):
        self.bucket = boto.connect_s3().get_bucket(bucket)
        self.secret = secret

        self.url = 'http://' + self.bucket.get_website_endpoint()
        if secret:
            self.url += '/' + secret

    def _key(self, package, filename):
        path = '%s/%s' % (package.name, filename)
        return Key(self.bucket, '%s/%s' % (self.secret, path) if self.secret else path)

    def get_index(self, package):
        try:
            html = self._key(package, 'index.html').get_contents_as_string()
            return Index.parse(self.url, html)
        except S3ResponseError:
            return Index(self.url, [])

    def put_index(self, package, index):
        k = self._key(package, 'index.html')
        k.set_metadata('Content-Type', 'text/html')
        k.set_metadata('Cache-Control', 'public, must-revalidate, proxy-revalidate, max-age=0')
        k.set_contents_from_string(index.to_html())
        k.set_acl('public-read')

    def put_package(self, package):
        for filename in package.files:
            k = self._key(package, filename)
            k.set_metadata('Content-Type', 'application/x-gzip')
            k.set_contents_from_filename(os.path.join('dist', filename))
            k.set_acl('public-read')

import os

import boto3
from botocore.exceptions import ClientError

from s3pypi.package import Index

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


class S3Storage(object):
    """Abstraction for storing package archives and index files in an S3 bucket."""

    def __init__(self, bucket, secret=None, region=None):
        self.s3 = boto3.resource('s3', region_name=region)
        self.bucket = bucket
        self.secret = secret

    def _object(self, package, filename):
        path = '%s/%s' % (package.name, filename)
        return self.s3.Object(self.bucket, '%s/%s' % (self.secret, path) if self.secret else path)

    def get_index(self, package):
        try:
            html = self._object(package, 'index.html').get()['Body'].read()
            return Index.parse(html)
        except ClientError:
            return Index([])

    def put_index(self, package, index):
        self._object(package, 'index.html').put(
            Body=index.to_html(),
            ContentType='text/html',
            CacheControl='public, must-revalidate, proxy-revalidate, max-age=0',
            ACL='public-read'
        )

    def put_package(self, package):
        for filename in package.files:
            with open(os.path.join('dist', filename)) as f:
                self._object(package, filename).put(
                    Body=f,
                    ContentType='application/x-gzip',
                    ACL='public-read'
                )

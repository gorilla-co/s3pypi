import os
import logging

import boto3
from botocore.exceptions import ClientError

from s3pypi.package import Index

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'

log = logging.getLogger()


class S3Storage(object):
    """Abstraction for storing package archives and index files in an S3 bucket."""

    def __init__(self, bucket, secret=None, region=None, bare=False, private=False, profile=None):
        if profile:
            boto3.setup_default_session(profile_name=profile)
        self.s3 = boto3.resource('s3', region_name=region)
        self.bucket = bucket
        self.secret = secret
        self.index = '' if bare else 'index.html'
        self.acl = 'private' if private else 'public-read'

    def _object(self, package, filename):
        path = '%s/%s' % (package.directory, filename)
        return self.s3.Object(self.bucket, '%s/%s' % (self.secret, path) if self.secret else path)

    def get_index(self, package):
        try:
            html = self._object(package, self.index).get()['Body'].read().decode('utf-8')
            return Index.parse(html)
        except ClientError:
            return Index([])

    def put_index(self, package, index):
        self._object(package, self.index).put(
            Body=index.to_html(),
            ContentType='text/html',
            CacheControl='public, must-revalidate, proxy-revalidate, max-age=0',
            ACL=self.acl
        )

    def put_package(self, package):
        for filename in package.files:
            log.debug("Uploading file `{}`...".format(filename))
            with open(os.path.join('dist', filename), mode='rb') as f:
                self._object(package, filename).put(
                    Body=f,
                    ContentType='application/x-gzip',
                    ACL=self.acl
                )

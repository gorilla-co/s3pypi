import logging
import os

import boto3
from botocore.exceptions import ClientError

from s3pypi.package import Index

log = logging.getLogger()


class S3Storage(object):
    """Abstraction for storing package archives and index files in an S3 bucket."""

    def __init__(
        self, bucket, secret=None, region=None, bare=False, private=False, profile=None
    ):
        if profile:
            boto3.setup_default_session(profile_name=profile)
        self.s3 = boto3.resource("s3", region_name=region)
        self.bucket = bucket
        self.secret = secret
        self.index = "" if bare else "index.html"
        self.acl = "private" if private else "public-read"

    def _object(self, package, filename):
        path = "%s/%s" % (package.directory, filename)
        return self.s3.Object(
            self.bucket, "%s/%s" % (self.secret, path) if self.secret else path
        )

    def get_index(self, package):
        try:
            html = (
                self._object(package, self.index).get()["Body"].read().decode("utf-8")
            )
            return Index.parse(html)
        except ClientError:
            return Index([])

    def put_index(self, package, index):
        self._object(package, self.index).put(
            Body=index.to_html(),
            ContentType="text/html",
            CacheControl="public, must-revalidate, proxy-revalidate, max-age=0",
            ACL=self.acl,
        )

    def put_package(self, package, dist_path=None):
        for filename in package.files:
            path = os.path.join(dist_path or "dist", filename)
            log.debug("Uploading file `{}`...".format(path))
            with open(path, mode="rb") as f:
                self._object(package, filename).put(
                    Body=f, ContentType="application/x-gzip", ACL=self.acl
                )

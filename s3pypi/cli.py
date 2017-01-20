from __future__ import print_function

import argparse
import sys

from s3pypi import __prog__, __version__
from s3pypi.exceptions import S3PyPiError
from s3pypi.package import Package
from s3pypi.storage import S3Storage

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


def create_and_upload_package(args):
    package = Package.create(args.wheel)
    storage = S3Storage(args.bucket, args.secret, args.region)

    index = storage.get_index(package)
    index.add_package(package, args.force)

    storage.put_package(package)
    storage.put_index(package, index)


def main():
    p = argparse.ArgumentParser(prog=__prog__, version=__version__)
    p.add_argument('--bucket', required=True, help='S3 bucket')
    p.add_argument('--secret', help='S3 secret')
    p.add_argument('--region', help='S3 region')
    p.add_argument('--force', action='store_true', help='Overwrite existing packages')
    p.add_argument('--no-wheel', dest='wheel', action='store_false', help='Skip wheel distribution')
    args = p.parse_args()

    try:
        create_and_upload_package(args)
    except S3PyPiError as e:
        print('error: %s' % e)
        sys.exit(1)

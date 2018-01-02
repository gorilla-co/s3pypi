from __future__ import print_function

import argparse
import sys

from s3pypi import __prog__
from s3pypi.exceptions import S3PyPiError
from s3pypi.package import Package
from s3pypi.storage import S3Storage

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


def create_and_upload_package(args):
    package = Package.create(args.wheel, args.sdist)
    storage = S3Storage(args.bucket, args.secret, args.region, args.bare, args.private, args.profile)

    index = storage.get_index(package)
    index.add_package(package, args.force)

    storage.put_package(package)
    storage.put_index(package, index)


def parse_args(raw_args):
    p = argparse.ArgumentParser(prog=__prog__)
    p.add_argument('--bucket', required=True, help='S3 bucket')
    p.add_argument('--secret', help='S3 secret')
    p.add_argument('--region', help='AWS region')
    p.add_argument('--profile', help='AWS profile')
    p.add_argument('--force', action='store_true', help='Overwrite existing packages')
    p.add_argument('--no-wheel', dest='wheel', action='store_false', help='Skip wheel distribution')
    p.add_argument('--no-sdist', dest='sdist', action='store_false', help='Skip sdist distribution')
    p.add_argument('--bare', action='store_true', help='Store index as bare package name')
    p.add_argument('--private', action='store_true', help='Store S3 Keys as private objects')
    return p.parse_args(raw_args)


def main():
    args = parse_args(sys.argv[1:])

    try:
        create_and_upload_package(args)
    except S3PyPiError as e:
        print('error: %s' % e)
        sys.exit(1)

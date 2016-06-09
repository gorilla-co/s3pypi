#!/usr/bin/env python
import argparse

from s3pypi import __prog__, __version__
from s3pypi.package import Package
from s3pypi.storage import S3Storage

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


def main():
    p = argparse.ArgumentParser(prog=__prog__, version=__version__)
    p.add_argument('--bucket', required=True, help='S3 bucket')
    p.add_argument('--secret', help='S3 secret')
    p.add_argument('--no-wheel', dest='wheel', action='store_false', help='Skip wheel distribution')
    args = p.parse_args()

    package = Package.create(args.wheel)
    storage = S3Storage(args.bucket, args.secret)

    index = storage.get_index(package)
    index.packages.discard(package)
    index.packages.add(package)

    storage.put_package(package)
    storage.put_index(package, index)


if __name__ == '__main__':
    main()

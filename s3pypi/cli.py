#!/usr/bin/env python
import argparse

from s3pypi import __prog__, __version__
from s3pypi.package import Package
from s3pypi.storage import S3Storage


def main():
    p = argparse.ArgumentParser(prog=__prog__, version=__version__)
    p.add_argument('--bucket', required=True, help='S3 bucket')
    p.add_argument('--secret', help='S3 secret')
    args = p.parse_args()

    package = Package.create()
    storage = S3Storage(args.bucket, args.secret)

    index = storage.get_index(package)
    index.packages.add(package)

    storage.put_package(package)
    storage.put_index(package, index)


if __name__ == '__main__':
    main()

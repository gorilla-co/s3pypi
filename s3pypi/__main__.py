from __future__ import print_function

import argparse
import logging
import sys
from pathlib import Path

from s3pypi import __prog__, __version__, core

logging.basicConfig()
log = logging.getLogger()


def parse_args(args):
    p = argparse.ArgumentParser(prog=__prog__)
    p.add_argument(
        "dist",
        nargs="+",
        type=Path,
        help="The distribution files to upload to S3. Usually `dist/*`.",
    )
    p.add_argument("-b", "--bucket", required=True, help="The S3 bucket to upload to.")
    p.add_argument("--profile", help="Optional AWS profile to use.")
    p.add_argument("--region", help="Optional AWS region to target.")
    p.add_argument("--prefix", help="Optional prefix to use for S3 object names.")
    p.add_argument("--acl", help="Optional canned ACL to use for S3 objects.")
    p.add_argument(
        "--unsafe-s3-website",
        action="store_true",
        help=(
            "Store the index as an S3 object named `<package>/index.html` instead of `<package>/`. "
            "This option is provided for backwards compatibility with S3 website endpoints, "
            "the use of which is discouraged because they require the bucket to be publicly accessible. "
            "It's recommended to instead use a private S3 bucket with a CloudFront Origin Access Identity."
        ),
    )
    p.add_argument("--force", action="store_true", help="Overwrite existing packages.")
    p.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    p.add_argument("--version", action="version", version=__version__)
    return p.parse_args(args)


def main(*args):
    kwargs = vars(parse_args(args or sys.argv[1:]))
    log.setLevel(logging.DEBUG if kwargs.pop("verbose") else logging.INFO)

    try:
        core.upload_packages(**kwargs)
    except core.S3PyPiError as e:
        print("error: %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()

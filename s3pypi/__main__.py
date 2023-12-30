from __future__ import print_function

import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict

from s3pypi import __prog__, __version__, core

logging.basicConfig()
log = logging.getLogger(__prog__)


def string_dict(text: str) -> Dict[str, str]:
    return dict(tuple(item.strip().split("=", 1)) for item in text.split(","))  # type: ignore


def build_arg_parser() -> ArgumentParser:
    p = ArgumentParser(prog=__prog__)
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
    p.add_argument("--s3-endpoint-url", help="Optional custom S3 endpoint URL.")
    p.add_argument(
        "--s3-put-args",
        type=string_dict,
        default={},
        help=(
            "Optional extra arguments to S3 PutObject calls. Example: "
            "'ServerSideEncryption=aws:kms,SSEKMSKeyId=1234...'"
        ),
    )
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
    p.add_argument(
        "-l",
        "--lock-indexes",
        action="store_true",
        help=(
            "Lock index objects in S3 using a DynamoDB table named `<bucket>-locks`. "
            "This ensures that concurrent invocations of s3pypi do not overwrite each other's changes."
        ),
    )
    p.add_argument(
        "--put-root-index",
        action="store_true",
        help="Write a root index that lists all available package names.",
    )
    p.add_argument(
        "--no-sign-request",
        action="store_true",
        help="Don't use authentication when communicating with S3.",
    )

    g = p.add_mutually_exclusive_group()
    g.add_argument(
        "--strict",
        action="store_true",
        help="Fail when trying to upload existing files.",
    )
    g.add_argument(
        "-f", "--force", action="store_true", help="Overwrite existing files."
    )

    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
    p.add_argument("-V", "--version", action="version", version=__version__)
    return p


def main(*raw_args: str) -> None:
    args = build_arg_parser().parse_args(raw_args or sys.argv[1:])
    log.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    cfg = core.Config(
        dist=args.dist,
        s3=core.S3Config(
            bucket=args.bucket,
            prefix=args.prefix,
            endpoint_url=args.s3_endpoint_url,
            put_kwargs=args.s3_put_args,
            unsafe_s3_website=args.unsafe_s3_website,
            no_sign_request=args.no_sign_request,
        ),
        strict=args.strict,
        force=args.force,
        lock_indexes=args.lock_indexes,
        put_root_index=args.put_root_index,
        profile=args.profile,
        region=args.region,
    )
    if args.acl:
        cfg.s3.put_kwargs["ACL"] = args.acl

    try:
        core.upload_packages(cfg)
    except core.S3PyPiError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()

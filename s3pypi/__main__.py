from __future__ import print_function

import logging
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Callable, Dict

from s3pypi import __prog__, __version__, core

logging.basicConfig()
log = logging.getLogger(__prog__)


def string_dict(text: str) -> Dict[str, str]:
    return dict(tuple(item.strip().split("=", 1)) for item in text.split(","))  # type: ignore


def build_arg_parser() -> ArgumentParser:
    p = ArgumentParser(prog=__prog__)
    p.add_argument("-V", "--version", action="version", version=__version__)
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")

    commands = p.add_subparsers(help="Commands", required=True)

    def add_command(
        func: Callable[[core.Config, Namespace], None], help: str
    ) -> ArgumentParser:
        name = func.__name__.replace("_", "-")
        cmd = commands.add_parser(name, help=help)
        cmd.set_defaults(func=func)
        return cmd

    up = add_command(upload, help="Upload packages to S3.")
    up.add_argument(
        "dist",
        nargs="+",
        type=Path,
        help="The distribution files to upload to S3. Usually `dist/*`.",
    )
    build_s3_args(up)
    up.add_argument(
        "--put-root-index",
        action="store_true",
        help="Write a root index that lists all available package names.",
    )
    g = up.add_mutually_exclusive_group()
    g.add_argument(
        "--strict",
        action="store_true",
        help="Fail when trying to upload existing files.",
    )
    g.add_argument(
        "-f", "--force", action="store_true", help="Overwrite existing files."
    )

    d = add_command(delete, help="Delete packages from S3.")
    d.add_argument("name", help="Package name.")
    d.add_argument("version", help="Package version.")
    build_s3_args(d)

    ul = add_command(force_unlock, help="Release a stuck lock in DynamoDB.")
    ul.add_argument("table", help="DynamoDB table.")
    ul.add_argument("lock_id", help="ID of the lock to release.")
    build_aws_args(ul)

    return p


def build_aws_args(p: ArgumentParser) -> None:
    p.add_argument("--profile", help="Optional AWS profile to use.")
    p.add_argument("--region", help="Optional AWS region to target.")


def build_s3_args(p: ArgumentParser) -> None:
    p.add_argument("-b", "--bucket", required=True, help="The S3 bucket to upload to.")
    p.add_argument("--prefix", help="Optional prefix to use for S3 object names.")

    build_aws_args(p)
    p.add_argument(
        "--no-sign-request",
        action="store_true",
        help="Don't use authentication when communicating with S3.",
    )
    p.add_argument(
        "--s3-endpoint-url", metavar="URL", help="Optional custom S3 endpoint URL."
    )
    p.add_argument(
        "--s3-put-args",
        metavar="ARGS",
        type=string_dict,
        default={},
        help=(
            "Optional extra arguments to S3 PutObject calls. Example: "
            "'ACL=public-read,ServerSideEncryption=aws:kms,SSEKMSKeyId=1234...'"
        ),
    )
    p.add_argument(
        "--index.html",
        dest="index_html",
        action="store_true",
        help=(
            "Store index pages with suffix `/index.html` instead of `/`. "
            "This provides compatibility with custom HTTPS proxies or S3 website endpoints."
        ),
    )
    p.add_argument(
        "--locks-table",
        metavar="TABLE",
        help="DynamoDB table to use for locking (default: `<bucket>-locks`).",
    )


def upload(cfg: core.Config, args: Namespace) -> None:
    core.upload_packages(
        cfg,
        args.dist,
        put_root_index=args.put_root_index,
        strict=args.strict,
        force=args.force,
    )


def delete(cfg: core.Config, args: Namespace) -> None:
    core.delete_package(cfg, name=args.name, version=args.version)


def force_unlock(cfg: core.Config, args: Namespace) -> None:
    core.force_unlock(cfg, args.table, args.lock_id)


def main(*raw_args: str) -> None:
    args = build_arg_parser().parse_args(raw_args or sys.argv[1:])
    log.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    cfg = core.Config(
        s3=core.S3Config(
            bucket=args.bucket,
            prefix=args.prefix,
            profile=args.profile,
            region=args.region,
            no_sign_request=args.no_sign_request,
            endpoint_url=args.s3_endpoint_url,
            put_kwargs=args.s3_put_args,
            index_html=args.index_html,
            locks_table=args.locks_table,
        )
        if hasattr(args, "bucket")
        else core.S3Config(
            bucket="",
            profile=args.profile,
            region=args.region,
        ),
    )

    try:
        args.func(cfg, args)
    except core.S3PyPiError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()

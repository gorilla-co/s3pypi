#!/usr/bin/env python
import argparse
import getpass
import json
import secrets
import sys
from dataclasses import asdict

import boto3

from handler import User, hash_password, region


def get_arg_parser():
    p = argparse.ArgumentParser()
    p.add_argument("domain", help="S3PyPI domain")
    p.add_argument("username", help="Username")
    pw = p.add_mutually_exclusive_group()
    pw.add_argument(
        "--password-stdin", action="store_true", help="Read password from stdin"
    )
    pw.add_argument(
        "--random-password",
        metavar="N",
        type=int,
        default=0,
        help="Generate a random password of N bytes",
    )
    p.add_argument(
        "--salt-nbytes",
        metavar="N",
        type=int,
        default=32,
        help="Length of the random salt in bytes",
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing users")
    return p


def main():
    args = get_arg_parser().parse_args()

    if args.password_stdin:
        password = sys.stdin.read().strip("\n")
    elif args.random_password:
        password = secrets.token_urlsafe(args.random_password)
    else:
        password = getpass.getpass()

    salt = secrets.token_urlsafe(args.salt_nbytes)

    user = User(
        username=args.username,
        password_hash=hash_password(password, salt),
        password_salt=salt,
    )
    put_user(args.domain, user, args.overwrite)

    if args.random_password:
        print(password)


def put_user(domain: str, user: User, overwrite: bool = False):
    data = asdict(user)
    username = data.pop("username")
    boto3.client("ssm", region_name=region).put_parameter(
        Name=f"/s3pypi/{domain}/users/{username}",
        Value=json.dumps(data, indent=2),
        Type="SecureString",
        Overwrite=overwrite,
    )


if __name__ == "__main__":
    main()

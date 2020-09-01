import pytest

from s3pypi.__main__ import parse_args


def test_cli_argparser_raises_no_exceptions():
    """An invalid keyword to ArgumentParser was causing an exception in Python 3."""
    with pytest.raises(SystemExit):
        parse_args(None)


def test_cli_argparser_raises_mutually_exclusive_exception():
    with pytest.raises(SystemExit):
        parse_args(["--bucket", "foo", "--acl", "public-read", "--private"])

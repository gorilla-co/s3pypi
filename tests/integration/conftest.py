import os
from contextlib import contextmanager

import boto3
import pytest
from moto import mock_s3


@pytest.fixture(scope="session")
def chdir():
    @contextmanager
    def _chdir(path):
        orig = os.getcwd()
        os.chdir(path)
        try:
            yield
        finally:
            os.chdir(orig)

    return _chdir


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def s3_bucket(aws_credentials):
    with mock_s3():
        conn = boto3.resource("s3", region_name="us-east-1")
        bucket = conn.Bucket("s3pypi-test")
        bucket.create()
        yield bucket


@pytest.fixture
def boto3_session(s3_bucket):
    return boto3.session.Session()

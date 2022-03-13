import os
from contextlib import contextmanager

import boto3
import moto
import pytest


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
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_bucket(aws_credentials):
    with moto.mock_s3():
        s3 = boto3.resource("s3")
        bucket = s3.Bucket("s3pypi-test")
        bucket.create()
        yield bucket


@pytest.fixture
def dynamodb_table(s3_bucket):
    name = f"{s3_bucket.name}-locks"
    with moto.mock_dynamodb2(), moto.mock_sts():
        db = boto3.resource("dynamodb")
        db.create_table(
            TableName=name,
            AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield db.Table(name)


@pytest.fixture
def boto3_session(s3_bucket):
    return boto3.session.Session()

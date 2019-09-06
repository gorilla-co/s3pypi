import os
import shutil
import tempfile
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


@pytest.fixture(scope="session")
def project_dir(chdir):
    projects_dir = os.path.join(os.path.dirname(__file__), "..", "data", "projects")

    @contextmanager
    def _project_dir(name):
        tmp_dir = tempfile.mkdtemp()
        try:
            src_dir = os.path.join(projects_dir, name)
            dst_dir = os.path.join(tmp_dir, name)
            shutil.copytree(src_dir, dst_dir)
            with chdir(dst_dir):
                yield dst_dir
        finally:
            shutil.rmtree(tmp_dir)

    return _project_dir


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture
def s3_bucket(aws_credentials):
    with mock_s3():
        conn = boto3.resource("s3")
        bucket = conn.Bucket("s3pypi-test")
        bucket.create()
        yield bucket

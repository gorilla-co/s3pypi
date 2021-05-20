import pytest

from s3pypi.locking import DynamoDBLocker, DynamoDBLockTimeoutError


def test_dynamodb_lock_timeout(boto3_session, dynamodb_table):
    lock = DynamoDBLocker(
        boto3_session,
        dynamodb_table.name,
        retry_delay=0,
        max_attempts=3,
    )
    key = "example"

    with lock(key):
        with pytest.raises(DynamoDBLockTimeoutError):
            with lock(key):
                pass

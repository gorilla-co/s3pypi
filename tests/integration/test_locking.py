import pytest

from s3pypi.locking import (
    DummyLocker,
    DynamoDBLocker,
    DynamoDBLockTimeoutError,
    LockerConfig,
)


def test_dynamodb_discover_found(boto3_session, dynamodb_table):
    lock = DynamoDBLocker.build(boto3_session, dynamodb_table.name, discover=True)

    assert isinstance(lock, DynamoDBLocker)
    assert lock.table == dynamodb_table


def test_dynamodb_discover_not_found(boto3_session):
    lock = DynamoDBLocker.build(
        boto3_session, table_name="does-not-exist", discover=True
    )
    assert isinstance(lock, DummyLocker)


def test_dynamodb_lock_timeout(dynamodb_table):
    cfg = LockerConfig(retry_delay=0, max_attempts=3)
    lock = DynamoDBLocker(dynamodb_table, owner="pytest", cfg=cfg)
    key = "example"

    with lock(key):
        with pytest.raises(DynamoDBLockTimeoutError):
            with lock(key):
                pass

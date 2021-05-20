import abc
import datetime as dt
import hashlib
import json
import logging
import time
from contextlib import contextmanager

import boto3

from s3pypi import __prog__, exceptions as exc

log = logging.getLogger(__prog__)


class Locker(abc.ABC):
    @contextmanager
    def __call__(self, key: str):
        lock_id = hashlib.sha1(key.encode()).hexdigest()
        self._lock(lock_id)
        try:
            yield
        finally:
            self._unlock(lock_id)

    @abc.abstractmethod
    def _lock(self, lock_id: str):
        ...

    @abc.abstractmethod
    def _unlock(self, lock_id: str):
        ...


class DummyLocker(Locker):
    def _lock(self, lock_id: str):
        pass

    _unlock = _lock


class DynamoDBLocker(Locker):
    def __init__(
        self,
        session: boto3.session.Session,
        table: str,
        retry_delay: int = 1,
        max_attempts: int = 10,
    ):
        db = session.resource("dynamodb")
        self.table = db.Table(table)
        self.exc = self.table.meta.client.exceptions
        self.retry_delay = retry_delay
        self.max_attempts = max_attempts
        self.caller_id = session.client("sts").get_caller_identity()["Arn"]

    def _lock(self, lock_id: str):
        for attempt in range(1, self.max_attempts + 1):
            now = dt.datetime.now(dt.timezone.utc)
            try:
                self.table.put_item(
                    Item={
                        "LockID": lock_id,
                        "AcquiredAt": now.isoformat(),
                        "Owner": self.caller_id,
                    },
                    ConditionExpression="attribute_not_exists(LockID)",
                )
                return
            except self.exc.ConditionalCheckFailedException:
                if attempt == 1:
                    log.info("Waiting to acquire lock... (%s)", lock_id)
                if attempt < self.max_attempts:
                    time.sleep(self.retry_delay)

        item = self.table.get_item(Key={"LockID": lock_id})["Item"]
        raise DynamoDBLockTimeoutError(self.table.name, item)

    def _unlock(self, lock_id: str):
        self.table.delete_item(Key={"LockID": lock_id})


class DynamoDBLockTimeoutError(exc.S3PyPiError):
    def __init__(self, table: str, item: dict):
        key = json.dumps({"LockID": {"S": item["LockID"]}})
        super().__init__(
            f"Timed out trying to acquire lock:\n\n{json.dumps(item, indent=2)}\n\n"
            "Another instance of s3pypi may currently be holding the lock.\n"
            "If this is not the case, you may release the lock as follows:\n\n"
            f"$ aws dynamodb delete-item --table-name {table} --key '{key}'\n"
        )

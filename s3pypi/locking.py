import abc
import datetime as dt
import getpass
import time
from contextlib import contextmanager

import boto3


class LockTimeoutError(Exception):
    def __init__(self, lock_id: str):
        super().__init__(f"Timed out trying to acquire lock '{lock_id}'")


class Locker(abc.ABC):
    @contextmanager
    def __call__(self, lock_id: str):
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
        poll_interval: int = 1,
        max_attempts: int = 30,
    ):
        db = session.resource("dynamodb")
        self.table = db.Table(table)
        self.exc = self.table.meta.client.exceptions
        self.poll_interval = poll_interval
        self.max_attempts = max_attempts
        self.user = getpass.getuser()

    def _lock(self, lock_id: str):
        for attempt in range(1, self.max_attempts + 1):
            now = dt.datetime.now(dt.timezone.utc)
            try:
                self.table.put_item(
                    Item={
                        "LockID": lock_id,
                        "AcquiredAt": now.isoformat(),
                        "Username": self.user,
                    },
                    ConditionExpression="attribute_not_exists(LockID)",
                )
                return
            except self.exc.ConditionalCheckFailedException:
                if attempt < self.max_attempts:
                    time.sleep(self.poll_interval)

        raise LockTimeoutError(lock_id)

    def _unlock(self, lock_id: str):
        self.table.delete_item(Item={"LockID": lock_id})

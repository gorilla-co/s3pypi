import abc
import datetime as dt
import getpass
import hashlib
import json
import logging
import socket
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import boto3
from mypy_boto3_dynamodb.service_resource import Table

from s3pypi import __prog__, exceptions as exc

log = logging.getLogger(__prog__)


class Locker(abc.ABC):
    @contextmanager
    def __call__(self, key: str) -> Iterator[None]:
        lock_id = hashlib.sha1(key.encode()).hexdigest()
        self._lock(lock_id)
        try:
            yield
        finally:
            self._unlock(lock_id)

    @abc.abstractmethod
    def _lock(self, lock_id: str) -> None:
        ...

    @abc.abstractmethod
    def _unlock(self, lock_id: str) -> None:
        ...


class DummyLocker(Locker):
    def _lock(self, lock_id: str) -> None:
        pass

    _unlock = _lock


@dataclass
class LockerConfig:
    retry_delay: int = 1
    max_attempts: int = 10


class DynamoDBLocker(Locker):
    @staticmethod
    def build(
        session: boto3.session.Session,
        table_name: str,
        discover: bool = False,
        cfg: LockerConfig = LockerConfig(),
    ) -> Locker:
        db = session.resource("dynamodb")
        table = db.Table(table_name)

        if discover:
            try:
                table.get_item(Key={"LockID": "?"})
            except table.meta.client.exceptions.ClientError:
                log.debug("No locks table found. Locking disabled.")
                return DummyLocker()

        owner = f"{getpass.getuser()}@{socket.gethostname()}"
        return DynamoDBLocker(table, owner, cfg)

    def __init__(self, table: Table, owner: str, cfg: LockerConfig):
        self.table = table
        self.exc = self.table.meta.client.exceptions
        self.owner = owner
        self.cfg = cfg

    def _lock(self, lock_id: str) -> None:
        for attempt in range(1, self.cfg.max_attempts + 1):
            now = dt.datetime.now(dt.timezone.utc)
            try:
                self.table.put_item(
                    Item={
                        "LockID": lock_id,
                        "AcquiredAt": now.isoformat(),
                        "Owner": self.owner,
                    },
                    ConditionExpression="attribute_not_exists(LockID)",
                )
                return
            except self.exc.ConditionalCheckFailedException:
                if attempt == 1:
                    log.info("Waiting to acquire lock... (%s)", lock_id)
                if attempt < self.cfg.max_attempts:
                    time.sleep(self.cfg.retry_delay)

        item = self.table.get_item(Key={"LockID": lock_id})["Item"]
        raise DynamoDBLockTimeoutError(self.table.name, item)

    def _unlock(self, lock_id: str) -> None:
        self.table.delete_item(Key={"LockID": lock_id})


class DynamoDBLockTimeoutError(exc.S3PyPiError):
    def __init__(self, table: str, item: dict):
        super().__init__(
            f"Timed out trying to acquire lock:\n\n{json.dumps(item, indent=2)}\n\n"
            "Another instance of s3pypi may currently be holding the lock.\n"
            "If this is not the case, you may release the lock as follows:\n\n"
            f"$ s3pypi force-unlock {table} {item['LockID']}\n"
        )

import abc
from contextlib import contextmanager

import boto3


class Locker(abc.ABC):
    @contextmanager
    def __call__(self, key: str):
        self._lock(key)
        try:
            yield
        finally:
            self._unlock(key)

    @abc.abstractmethod
    def _lock(self, key: str):
        ...

    @abc.abstractmethod
    def _unlock(self, key: str):
        ...


class DummyLocker(Locker):
    def _lock(self, key: str):
        pass

    _unlock = _lock


class DynamoDbLocker(Locker):
    def __init__(
        self,
        session: boto3.session.Session,
        table: str,
        timeout: int = 10,
    ):
        db = session.resource("dynamodb")
        self.table = db.Table(table)
        self.timeout = timeout

    def _lock(self, key: str):
        raise NotImplementedError

    def _unlock(self, key: str):
        raise NotImplementedError

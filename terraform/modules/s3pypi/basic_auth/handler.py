import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Self

import boto3

log = logging.getLogger()

region = "us-east-1"


def handle(event: dict, context) -> dict:
    request = event["Records"][0]["cf"]["request"]
    try:
        authenticate(request["headers"])
    except Exception as e:
        log.error(repr(e))
        return unauthorized
    return request


def authenticate(headers: dict) -> None:
    domain = headers["host"][0]["value"]
    auth = BasicAuth.decode(headers["authorization"][0]["value"])
    user = get_user(domain, auth.username)

    if hash_password(auth.password, user.password_salt) != user.password_hash:
        raise ValueError("Invalid password for " + auth.username)


@dataclass(frozen=True)
class BasicAuth:
    username: str
    password: str

    @classmethod
    def decode(cls, header: str) -> Self:
        auth_type, tail = header.split(" ")
        if auth_type != "Basic":
            raise ValueError("Invalid auth type: " + auth_type)

        creds = base64.b64decode(tail).decode()
        return cls(*creds.split(":", 1))

    def encode(self) -> str:
        creds = f"{self.username}:{self.password}"
        return "Basic " + base64.b64encode(creds.encode()).decode()


@dataclass(frozen=True)
class User:
    username: str
    password_hash: str
    password_salt: str


@lru_cache(maxsize=1024)
def get_user(domain: str, username: str) -> User:
    data = boto3.client("ssm", region_name=region).get_parameter(
        Name=f"/s3pypi/{domain}/users/{username}",
        WithDecryption=True,
    )["Parameter"]["Value"]
    return User(username, **json.loads(data))


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha1((password + salt).encode()).hexdigest()


unauthorized = dict(
    status="401",
    statusDescription="Unauthorized",
    headers={
        "www-authenticate": [
            {"key": "WWW-Authenticate", "value": 'Basic realm="Login"'}
        ]
    },
)

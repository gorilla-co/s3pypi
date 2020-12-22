import base64
import hashlib
import json
import logging
from dataclasses import dataclass

import boto3

log = logging.getLogger()

region = "us-east-1"


def handle(event: dict, context):
    request = event["Records"][0]["cf"]["request"]
    try:
        authenticate(request["headers"])
    except Exception as e:
        log.error(repr(e))
        return unauthorized
    return request


def authenticate(headers: dict):
    domain = headers["host"][0]["value"]
    auth = headers["authorization"][0]["value"]
    auth_type, creds = auth.split(" ")

    if auth_type != "Basic":
        raise ValueError("Invalid auth type: " + auth_type)

    username, password = base64.b64decode(creds).decode().split(":")
    user = get_user(domain, username)

    if hash_password(password, user.password_salt) != user.password_hash:
        raise ValueError("Invalid password for " + username)


@dataclass
class User:
    username: str
    password_hash: str
    password_salt: str


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

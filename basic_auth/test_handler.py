import logging
from unittest.mock import patch

import handler


def test_decode_password_with_colon():
    auth = handler.BasicAuth("alice", "my:password")
    assert handler.BasicAuth.decode(auth.encode()) == auth


def test_handle_success():
    resp = call_handler("secret", "secret")
    assert resp != handler.unauthorized
    assert resp["headers"]["authorization"]


def test_handle_unauthorized(caplog):
    resp = call_handler("wrong", "secret")
    assert resp == handler.unauthorized

    assert caplog.record_tuples == [
        ("root", logging.ERROR, "ValueError('Invalid password for alice')"),
    ]


def call_handler(password: str, expected_password: str, salt: str = "NaCl"):
    auth = handler.BasicAuth("alice", password)
    headers = {
        "host": [{"value": "pypi.example.com"}],
        "authorization": [{"value": auth.encode()}],
    }
    event = {"Records": [{"cf": {"request": {"headers": headers}}}]}

    def get_mock_user(_, username: str):
        return handler.User(
            username=username,
            password_hash=handler.hash_password(expected_password, salt),
            password_salt=salt,
        )

    with patch.object(handler, "get_user", get_mock_user):
        return handler.handle(event, context=None)

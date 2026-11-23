import put_user
import pytest


def test_username_with_colon_rejected(capsys):
    with pytest.raises(SystemExit):
        put_user.get_arg_parser().parse_args(["pypi.example.com", "user:alice"])

    assert "argument username: must not contain ':'" in capsys.readouterr().err

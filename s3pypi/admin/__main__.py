
import argparse
import getpass
import logging
import re
import sys
import typing as t

import boto3.session
import botocore.exceptions
import passlib.context
import passlib.utils
import urllib.parse

from ..admin import __prog__

__author__ = 'Christoph Ludwig'
__copyright__ = 'Copyright 2019, Haufe Group'
__license__ = 'MIT'

_log = logging.getLogger(__name__)

_user_entry_re: t.ClassVar[t.Pattern] = re.compile(r"^\s*(?P<username>\w[^:\s]*)\s*:\s*(?P<hash>\S+)\s*$")
_pw_ctx = passlib.context.CryptContext(schemes=['pbkdf2_sha256'])


class S3ObjectId(t.NamedTuple):
    bucket_name: str
    key: str


def get_aws_session(args: argparse.Namespace) -> boto3.session.Session:
    profile = getattr(args, 'profile', None)
    return boto3.session.Session(profile_name=profile)


def s3_object_id(s3_uri: str) -> S3ObjectId:
    """
    Split an S3 URI into the bucket name and the referenced object's key

    :param s3_uri: S3 URI
    :return: 2-tuple (bucket_name, key)
    """
    try:
        split_url = urllib.parse.urlsplit(s3_uri)
        bucket_name = split_url.netloc
        key = split_url.path.lstrip('/')
    except Exception as ex:
        raise ValueError(f'value cannot be parsed as an URI: {s3_uri}') from ex

    if split_url.scheme != 's3':
        raise ValueError(f'URI must use the s3 scheme: {s3_uri}')
    if not bucket_name:
        raise ValueError(f'URI must specify a bucket name: {s3_uri}')

    return S3ObjectId(bucket_name, key)


def build_user_store_object(args):
    bucket_name, key = getattr(args, 'userstore_uri', '')
    aws_session = get_aws_session(args)
    s3 = aws_session.resource('s3')
    _log.debug('constructing s3.Object(%s, %s)', bucket_name, key)
    user_store_object = s3.Object(bucket_name, key)
    return user_store_object


def s3_text_object_lines(s3_object, encoding='utf-8', raise_not_found=True) -> t.Iterator[str]:
    _log.debug('fetching the content of s3://%s/%s', s3_object.bucket_name, s3_object.key)
    try:
        response_dict = s3_object.get()
    except botocore.exceptions.ClientError as ex:
        response_meta = ex.response.get('ResponseMetadata', {})
        if response_meta.get('HTTPStatusCode') != 404 or raise_not_found:
            raise
        _log.info('missing s3 object s3://%s/%s treated as empty', s3_object.bucket_name, s3_object.key)
        return

    body_stream = response_dict.get('Body')
    if body_stream is None:
        _log.warning('received empty object body for s3://%s/%s', s3_object.bucket_name, s3_object.key)
        return

    try:
        for line in body_stream.iter_lines():
            yield line.decode(encoding).rstrip('\r\n')
    finally:
        _log.debug('closing the content of s3://%s/%s', s3_object.bucket_name, s3_object.key)
        body_stream.close()


def update_user_store(user_store_object, normalized_username, update_function, raise_object_not_found=True):
    def user_entry_predicate(line: str) -> bool:
        match = _user_entry_re.fullmatch(line)
        return match and match.group('username') == normalized_username

    try:
        lines = list(s3_text_object_lines(user_store_object, raise_not_found=raise_object_not_found))
        user_index = next((i for i, l in enumerate(lines) if user_entry_predicate(l)), -1)
        update_function(lines, user_index)
        if lines and re.search(r'\S', lines[-1]):
            lines.append('')
        body = '\n'.join(lines).encode('utf-8')
        user_store_object.put(Body=body)
    except botocore.exceptions.ClientError as ex:
        response_meta = ex.response.get('ResponseMetadata', {})
        if response_meta.get('HTTPStatusCode') != 404:
            raise
        _log.warning('s3 object s3://%s/%s not found', user_store_object.bucket_name, user_store_object.key)
        exit(3)


def list_users(args: argparse.Namespace) -> None:
    user_store_object = build_user_store_object(args)
    try:
        for line in s3_text_object_lines(user_store_object):
            entry_match = _user_entry_re.fullmatch(line)
            if entry_match:
                print(entry_match.group('username'))
    except botocore.exceptions.ClientError as ex:
        response_meta = ex.response.get('ResponseMetadata', {})
        if response_meta.get('HTTPStatusCode') != 404:
            raise
        _log.warning('s3 object s3://%s/%s not found', user_store_object.bucket_name, user_store_object.key)
        exit(3)


def set_password(args: argparse.Namespace) -> None:
    normalized_username = passlib.utils.saslprep(args.username, param='username')

    def add_or_replace_user_entry(lines: t.List[str], idx: int) -> None:
        if args.from_stdin:
            password = ''
            while not password:
                input_line = sys.stdin.readline()
                if not input_line:
                    break  # EOF
                password = input_line.rstrip('\r\n')
        else:
            password = getpass.getpass(f'Password for user {normalized_username}: ')
        normalized_password = passlib.utils.saslprep(password, param='password')
        if not normalized_password:
            _log.error('password must not be empty')
            exit(4)

        pw_hash = _pw_ctx.hash(normalized_password)
        new_entry = f'{normalized_username}:{pw_hash}'
        if 0 <= idx < len(lines):
            _log.debug('updating user store line %d with entry for user %s', idx + 1, normalized_username)
            lines[idx] = new_entry
        else:
            _log.debug('adding user store line %d with entry for user %s', len(lines), normalized_username)
            lines.append(new_entry)

    user_store_object = build_user_store_object(args)
    update_user_store(user_store_object, normalized_username, add_or_replace_user_entry, not args.create)


def delete_user(args: argparse.Namespace) -> None:
    normalized_username = passlib.utils.saslprep(args.username, param='username')

    def delete_user_entry(lines: t.List[str], idx: int) -> None:
        if 0 <= idx < len(lines):
            _log.debug('deleting user store line %d with entry for user %s', idx+1, normalized_username)
            del lines[idx]
        else:
            _log.info('no entry for user %s in use store', normalized_username)

    user_store_object = build_user_store_object(args)
    update_user_store(user_store_object, normalized_username, delete_user_entry)


def parse_args(raw_args: t.Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=__prog__,
                                     description='utility for managing the entries in the S3 PyPi user store')
    parser.add_argument('-p', '--profile',  help='optional name of the boto3 profile')
    parser.add_argument('-l', '--logfile', type=argparse.FileType(mode='a', bufsize=1, encoding='UTF-8'),
                        help='file the logs are appended to (default: stderr)')
    parser.add_argument('-v', '--verbose', action='store_true', help='turn on verbose logs.')
    parser.add_argument('-d', '--debug', action='store_true', help='turn on debug logs.')
    parser.add_argument('userstore_uri', metavar='USERSTORE_URI', type=s3_object_id,
                        help='S3-URI of the user store object')

    sp = parser.add_subparsers(dest='command', required=True)
    plist = sp.add_parser('list', help='list users')
    plist.set_defaults(handler=list_users)

    pset = sp.add_parser('set_password', help='adds or updates the specified user\'s entry in the user store')
    pset.add_argument('-c', '--create', action='store_true', help='create S3 object if it does not exist yet')
    pset.add_argument('-s', '--from-stdin', action='store_true', help='read pw from stdin')
    pset.add_argument('username', metavar='USERNAME', help='the name of the user')
    pset.set_defaults(handler=set_password)

    pdel = sp.add_parser('delete', help='delete any entry for the specified user from the user store')
    pdel.add_argument('username', metavar='USERNAME', help='the name of the user')
    pdel.set_defaults(handler=delete_user)

    return parser.parse_args(raw_args)


# noinspection DuplicatedCode
def initialize_logging(args):
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler = logging.StreamHandler(stream=args.logfile)
    log_handler.setFormatter(log_formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    root_logger.setLevel(log_level)


def main() -> None:
    args = parse_args(sys.argv[1:])
    initialize_logging(args)

    try:
        args.handler(args)
    except Exception as e:
        print('error: %s' % e)
        _log.fatal('application terminated due to an exception', exc_info=e)
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
User store proxy for client authentication
"""
import logging
import re
import time
import typing as t

import boto3
import botocore.exceptions
import botocore.response
import passlib.context
import passlib.utils

_log = logging.getLogger(__name__)


class S3UserStore:
    r"""
    Proxy for a user store object in an S3 bucket. The bucket's content is cached; if a configurable timespan
    passed since the last check, the content is synchronously reloaded from the bucket *if* the object changed.

    The bucket object is assumed to basically contain one user entry per UTF-8 encoded text line.
    User entries specify a username and a password according to the following regular expression::

        r"^\s*(?P<username>\w[^:\s]*)\s*:\s*(?P<hash>\S+)\s*$"

    All lines not matching this regular expression are ignored; more precisely, empty lines and lines starting
    with a `#` character following whitespace are silently skipped, all other non-matching lines
    are logged at warning level.
    """

    user_entry_re: t.ClassVar[t.Pattern] = re.compile(r"^\s*(?P<username>\w[^:\s]*)\s*:\s*(?P<hash>\S+)\s*$")

    def __init__(self,
                 bucket_name: str,
                 key: str,
                 refresh_period: float = 60.0,
                 aws_session: boto3.Session = None) -> None:
        """
        Initialize an S3 user store proxy object.

        :param bucket_name: the name of the S3 bucket the user store is part of
        :param key: the key of the user store in the S3 bucket
        :param refresh_period: the timespan (in seconds) after which the user store is checked for updates
        :param aws_session: an optional boto3 session that provides credentials for access to the bucket
        """
        self._bucket_name = bucket_name
        self._key = key

        if aws_session is None:
            aws_session = boto3.session.Session()
        self._s3 = aws_session.resource('s3')
        self._user_store_object = self._s3.Object(bucket_name, key)
        self.refresh_period = refresh_period
        self._etag = ''
        self._hashed_credentials = None
        self._last_update = time.time() - 2 * self.refresh_period
        self._pw_ctx = passlib.context.CryptContext(schemes=['pbkdf2_sha256'])

    @property
    def refresh_required(self) -> bool:
        """
        Computed flag that tells whether the last check for user store changes took place more than
        `self.refresh_period` seconds ago.

        :return: True if and only if the local copy of the user store data is stale.
        """
        return self._last_update + self.refresh_period < time.time()

    @property
    def hashed_credentials(self) -> t.Mapping[str, str]:
        """
        The mapping of user names to hashed password data found in the user store. The map is
        updated if the data is stale and the user store object changed in the S3 bucket.

        :return: mapping of user names to hashed credentials
        """
        if self._hashed_credentials is None or self.refresh_required:
            try:
                user_store_dict = self._user_store_object.get(IfNoneMatch=self._etag)
            except botocore.exceptions.ClientError as ex:
                response_meta = ex.response.get('ResponseMetadata', {})
                if response_meta.get('HTTPStatusCode') != 304:
                    raise
            else:
                if user_store_dict is not None:
                    self._etag = user_store_dict.get('ETag', '')
                    body_stream = user_store_dict.get('Body')
                    self._hashed_credentials = dict(self._user_hash_pairs(body_stream))

            # outside the else block because we need to update the time stamp in case of a 304 response as well
            self._last_update = time.time()

        return self._hashed_credentials

    @classmethod
    def _user_hash_pairs(cls, body: t.Optional[botocore.response.StreamingBody]) -> t.Iterator[t.Tuple[str, str]]:
        """
        Parse the provided response body and yield all username / password hash pairs found therein.

        :param body: a readable response body
        :return: an iterator over the username / password hash pairs found in the response body
        """
        if body is not None:
            try:
                for line in body.iter_lines():
                    line = line.decode('utf-8').strip()
                    if not line or line.startswith('#'):
                        continue
                    entry_match = cls.user_entry_re.fullmatch(line)
                    if entry_match:
                        username, pw_hash = entry_match.groups()
                        yield passlib.utils.saslprep(username, param='username'), pw_hash
                    else:
                        _log.warning(f'ignored ill-formatted user store entry "{line}"')
            finally:
                body.close()

    def verify_password(self, username: str, secret: str) -> bool:
        """
        Verify the password store contains an entry for the specified user and the user's password hash matches
        the specified secret.

        Both username and secret are normalized according to RFC 4013.

        :param username: the name of the user whose password is checked
        :param secret: the password
        :return: True if and only if the user store contains an entry matching the specified username / secret pair
        """
        try:
            hashed_creds = self.hashed_credentials
            if not hashed_creds:
                return False  # user store is empty or inaccessible
        except Exception as ex:
            _log.error('cannot access user store data', exc_info=ex)
            return False

        try:
            normalized_username = passlib.utils.saslprep(username, param='username')
            normalized_secret =  passlib.utils.saslprep(secret, param='secret')
            user_pwdata = self._hashed_credentials.get(normalized_username)
            if user_pwdata:
                return self._pw_ctx.verify(normalized_secret, user_pwdata)
            else:
                # avoid trivial timing attack to learn registered user names
                return self._pw_ctx.dummy_verify()
        except Exception as ex:
            _log.error('cannot verify provided password', exc_info=ex)
            return False
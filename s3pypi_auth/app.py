import functools
import logging
import typing as t

import basicauth
import boto3
import boto3.resources.base

import users

log = logging.getLogger(__name__)
log_level = logging.INFO  # no environment variable in CloudFront's Lambda@Edge
logging.getLogger().setLevel(log_level)  # set level at the root logger

log.debug('Loading function')


# "types" exclusively used for type hinting / static checks; at runtime, the objects will still be dicts!
Request = t.NewType('Request', t.Dict)
Response = t.NewType('Response', t.Dict)


UNAUTHORIZED_RESPONSE = Response({
    'status': '401',
    'statusDescription': 'Unauthorized',
    'headers': {
        'www-authenticate': [{'key': 'WWW-Authenticate', 'value': 'Basic'}]
    },
})


UNEXPECTED_EVENT_RESPONSE = Response({
    'status': '500',
    'statusDescription': 'Unexpected LambdaEdge event'
})


UNSUPPORTED_METHOD_RESPONSE = Response({
    'status': '405',
    'statusDescription': 'Method not allowed'
})


class UsernamePasswordCredentials(t.NamedTuple):
    username: str
    password: str


class AuthException(Exception):
    pass


class UnexpectEventException(Exception):
    pass


class UnsupportedMethodException(Exception):
    pass


@functools.lru_cache(maxsize=2)
def s3_user_store(distribution_id: str) -> users.S3UserStore:
    """
    Caching factory for `S3UserStore` instances based on the CloudFront distribution config.

    This function is a workaround for the fact that we cannot pass config as environment variables
    into Lambda@Edge functions; it therefore looks up the S3 bucket name from the distribution's
    origin configuration and caches the result for performance's sake.
    """
    aws_session = boto3.session.Session()
    cloudfront = aws_session.client('cloudfront')
    response = cloudfront.get_distribution_config(Id=distribution_id)
    distribution_config = response.get('DistributionConfig')
    origins = distribution_config.get('Origins', {}).get('Items', [])
    pypi_bucket_origin = next(filter(lambda origin: origin.get('Id') == 'PyPiS3BucketOrigin', origins), {})
    bucket_dn = pypi_bucket_origin.get('DomainName')
    bucket_name = bucket_dn.rsplit('.', maxsplit=4)[0]  # <bucket_name>.s3.<region>.amazonaws.com
    return users.S3UserStore(bucket_name, 'config/users', refresh_period=60.0, aws_session=aws_session)


def extract_event_data(event: t.Dict) -> t.Tuple[Request, str]:
    """
    Extract the HTTP request and the id of the CloudFormation distribution this Lambda@Edge function is part of.

    :param event: Lambda@Edge event that triggered the lambda function invocation
    :return: HTTP request and the distribution id
    :raises UnexpectedEventException: the event is not of type "viewer-request"
    """
    cf_event = event.get('Records', [{'cf': {}}])[0]['cf']

    cf_event_type = cf_event.get('config', {}).get('eventType')
    if not cf_event_type == 'viewer-request':
        raise UnexpectEventException(f'unexpected event type "{cf_event_type}"')

    distribution_id = cf_event.get('config', {}).get('distributionId', '')
    request = Request(cf_event.get('request', {}))
    return request, distribution_id


def get_header_value(request: Request, header_name: str) -> t.Optional[str]:
    """
    Get the value (if any) of the request's (first) header with the specified name.

    :param request: HTTP request
    :param header_name: (case-insensitive) header name
    :return: value of the request's first header with the specified name
    """
    # get header in lowercase
    authorization_header = {
        k.lower(): v
        for k, v in request.get('headers', {}).items()
        if k.lower() == header_name
    }.get(header_name)
    if authorization_header:
        return authorization_header[0].get('value')
    return None


def get_basic_auth_credentials(request: Request) -> t.Optional[UsernamePasswordCredentials]:
    """
    Get the username and password from the request's basic auth header (if any).

    :param request: HTTP request
    :return: username and password decoded from the value of the request's authorization header or None if the request
             has no such header
    :raises AuthException: cannot parse the authorization header value according to the Basic Auth scheme
    """
    try:
        credentials = get_header_value(request, 'authorization')
        if not credentials:
            return None
        return UsernamePasswordCredentials(*basicauth.decode(credentials))
    except Exception as ex:
        log.info('parsing of basic authorization header failed with an exception', exc_info=ex)
        raise AuthException('cannot decode basic auth header')


def method_filter(request: Request) -> Request:
    """
    Request filter that enforces the request method is either `GET` or `HEAD`.

    :param request: HTTP request
    :return: unmodified request
    :raises UnsupportedMethodException: the request method is neither GET nor HEAD
    """
    method = request.get('method')
    if method not in {'GET', 'HEAD'}:
        raise UnsupportedMethodException(f'unsupported method "{method}"')
    return request


def auth_filter(request: Request, user_store: users.S3UserStore) -> Request:
    """
    Request filter that enforces the presence of valid basic auth credentials.

    :param request: HTTP request
    :param user_store: user store presented basic auth credentials are validated against
    :return: unmodified request
    :raises AuthException: the request does not include valid basic auth credentials
    """
    credentials = get_basic_auth_credentials(request)
    if not credentials:
        raise AuthException('no authorization header')

    if not user_store.verify_password(*credentials):
        raise AuthException('unknown username / password')

    log.info('correct password from user %s', credentials.username)
    return request


def auto_index_filter(request: Request) -> Request:
    """
    Request filter that adds the segment "index.html" to any path that ends with "/".

    :param request: HTTP request
    :return: request with an extra path segment if the original path ended with '/'
    """
    path = request.get('uri', '')
    if path.endswith('/'):
        log.debug('auto-index: appended "index.html" to the request path')
        request['uri'] = path + 'index.html'
    return request


def lambda_handler(event: t.Dict, context: t.Dict) -> t.Union[Request, Response]:
    """
    PyPi S3 Authentication and Authorization filter. In addition, this viewer-request handler
    appends 'index.html' to all request paths ending in a '/'.

    Parameters
    ----------
    event: dict, required
        CloudFront viewer request event

        Event doc: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-event-structure.html#lambda-event-structure-request

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    The request object (possibly with an augmented path) if the user was successfully authenticated and is authorized
    to access the specified resource or a response object with an appropriate 4xx status code: dict

        Return doc: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-generating-http-responses.html
    """

    try:
        request, distribution_id = extract_event_data(event)
        user_store = s3_user_store(distribution_id)

        request = method_filter(request)
        request = auth_filter(request, user_store)
        return auto_index_filter(request)
    except AuthException as ex:
        log.info('access denied: %s', str(ex))
        return UNAUTHORIZED_RESPONSE
    except UnexpectEventException as ex:
        log.critical('Internal Error: %s', str(ex))
        return UNEXPECTED_EVENT_RESPONSE
    except UnsupportedMethodException as ex:
        log.info('request method denied: %s', str(ex))
        return UNSUPPORTED_METHOD_RESPONSE



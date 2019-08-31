import argparse
import sys
import logging
import re
import textwrap
import typing as t

import boto3.session

from ..infrastructure import __prog__
from .cloudformation import Parameter, CloudFormationService, SAM

__author__ = 'Christoph Ludwig'
__copyright__ = 'Copyright 2019, Haufe Group'
__license__ = 'MIT'

_log = logging.getLogger(__name__)


def parse_args(raw_args: t.Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=__prog__,
                                     description='deploy the CloudFormation templates that describe the S3 PyPi '
                                                 'infrastructure (i.e., S3 bucket, IAM roles and policies, '
                                                 'CloudFront distribution incl. Lambda@Edge function etc.)')
    parser.add_argument('-b', '--bucket',
                        help='optional name of the PyPi S3 bucket (if different from the domain name)')
    parser.add_argument('-p', '--profile',
                        help='optional name of the boto3 profile')
    parser.add_argument('-r', '--region',
                        help='optional AWS region where to deploy the non-global infrastructure')
    parser.add_argument('-v', '--verbose', action='store_true', help='turn on verbose output.')
    parser.add_argument('-d', '--debug', action='store_true', help='turn on debug output.')
    parser.add_argument('domain', help='the public domain name of the S3 PyPi repository '
                                       '(serves also as the name of the repository\'s S3 bucket '
                                       'unless the --bucket option is specified)')
    parser.add_argument('certificate_arn', help='ACM ARN of the certificate issued for the specified domain name '
                                                '(must be deployed in the region us-east-1!)')
    parser.add_argument('sam_bucket', help='name or ARN of S3 bucket used by SAM to upload Lambda functions '
                                           'to us-east-1')
    return parser.parse_args(raw_args)


def get_aws_session(profile: str = None, region: str = None) -> boto3.session.Session:
    return boto3.session.Session(profile_name=profile, region_name=region)


class OriginAccessIdAndPolicies(t.NamedTuple):
    origin_access_id: str
    publish_packages_policy: str
    manage_users_policy: str
    read_bucket_policy: str


def as_stack_name(name: str) -> str:
    """
    Transform the specified name into a valid CloudForm stack name (i.e., a name that matches the
    regular expression `[a-zA-Z][-a-zA-Z0-9]*`.

    :param name: the candidate name
    :return: a valid stack name
    """
    s = re.sub(r'[^-a-zA-Z0-9]+', '-', name)
    if re.match(r'^[^a-zA-Z]', s):
        prefix = 'stack' if s.startswith('-') else 'stack-'
        s = prefix + s
    return s


def deploy_bucket_and_roles(bucket_name: str,
                            cloudformation_service: CloudFormationService) -> OriginAccessIdAndPolicies:
    outputs = cloudformation_service.create_stack(
        stack_name=as_stack_name(f'{bucket_name}-bucket-and-policies'),
        template_name='s3-pypi-template.yaml',
        parameters=Parameter('PyPiS3BucketName', bucket_name),
        capabilities='CAPABILITY_NAMED_IAM',
        waiter_delay=10
    )
    return OriginAccessIdAndPolicies(origin_access_id=outputs.get('PyPiCloudFrontOriginAccessId'),
                                     publish_packages_policy=outputs.get('PublishS3PyPiPackagesPolicy'),
                                     manage_users_policy=outputs.get('ManageS3PyPiUserCredentialsPolicy'),
                                     read_bucket_policy=outputs.get('ReadS3PyPiBucketPolicy'))


# noinspection DuplicatedCode
def initialize_logging(args):
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_handler = logging.StreamHandler()
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
        regional_session = get_aws_session(profile=args.profile, region=args.region)
        regional_cf_service = CloudFormationService(regional_session)
        bucket_name = args.bucket or args.domain
        origin_access_id, publish_packages_policy, manage_users_policy, read_bucket_policy = \
            deploy_bucket_and_roles(bucket_name=bucket_name,
                                    cloudformation_service=regional_cf_service)

        virginia_session = get_aws_session(profile=args.profile, region='us-east-1')
        virginia_sam_service = SAM(virginia_session, args.sam_bucket)
        sam_outputs = virginia_sam_service.create_stack(
            stack_name=as_stack_name(f'{args.domain}-lambda-edge'),
            template_name='s3-pypi-auth-template.yaml',
            parameters=(
                Parameter('S3PyPiDomainName', args.domain),
                #s3pypi_cf.Parameter('ReadS3PyPiBucketPolicy', read_bucket_policy),
                Parameter('S3PyPiBucketName', bucket_name)
            ),
            capabilities=('CAPABILITY_NAMED_IAM', 'CAPABILITY_AUTO_EXPAND'),
            waiter_delay=10,
            use_container=True
        )
        auth_function_version = sam_outputs.get('S3PyPiAuthFunctionVersion')

        distr_outputs = regional_cf_service.create_stack(
            stack_name=as_stack_name(f'{args.domain}-cloudfront-distribution'),
            template_name='s3-pypi-cloudfront-template.yaml',
            parameters=(
                Parameter('DomainName', args.domain),
                Parameter('AcmCertificateArn', args.certificate_arn),
                Parameter('PyPiS3BucketName', bucket_name),
                Parameter('PyPiCloudFrontOriginAccessId', origin_access_id),
                Parameter('S3PyPiAuthFunctionVersion', auth_function_version)
            ),
            capabilities=None,
            waiter_delay=30,
            waiter_max_attempts=180
        )
        cname_record_value = distr_outputs.get('CNAMERecordValue')
        print(textwrap.dedent(f"""
          S3 PyPi infrastructure created: 
            S3 Bucket: {bucket_name}
            Publish Packages Policy: {publish_packages_policy}
            Manage PyPi Users Policy: {manage_users_policy}
            Read PyPi Bucket Policy: {read_bucket_policy}
            SAM deployment output: {sam_outputs}
            Distribution output: {distr_outputs}
            """))
    except Exception as e:
        print('error: %s' % e)
        _log.fatal('application terminated due to an exception', exc_info=e)
        sys.exit(1)


if __name__ == '__main__':
    main()

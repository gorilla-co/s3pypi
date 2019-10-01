"""
Convenience utilities for the creation of AWS CloudFormation stacks.
"""

import dataclasses
import logging
import os
import pathlib
import pprint
import subprocess
import typing as t

import boto3.resources.base
import boto3.session
import botocore.client
import botocore.waiter

_log = logging.getLogger(__name__)

# TODO: move templates as data files into the package and access them using pkg_resources
_PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).parents[
    len(__package__.split("."))
]
_TEMPLATE_SOURCE_FOLDER: pathlib.Path = _PROJECT_ROOT / "cloudformation"
_PACKAGED_TEMPLATES_FOLDER: pathlib.Path = _PROJECT_ROOT / "packaged_templates"


@dataclasses.dataclass(frozen=True)
class Parameter:
    """
    A CloudFormation stack template input parameter.
    """

    name: str
    value: t.Any = None
    use_previous: bool = False
    resolved_value: str = None

    def to_input_json(self) -> t.Dict[str, t.Union[str, bool]]:
        result = {"ParameterKey": self.name, "UsePreviousValue": self.use_previous}
        if self.value is not None:
            result["ParameterValue"] = self.value
        if self.resolved_value is not None:
            result["ResolvedValue"] = self.resolved_value
        return result


def _read_file(template_fs_path: t.Union[str, os.PathLike]) -> str:
    with open(os.fspath(template_fs_path), "r") as template_file:
        return "".join(template_file)


def template_source_path(name) -> pathlib.Path:
    return _TEMPLATE_SOURCE_FOLDER / name


def packaged_template_path(name) -> pathlib.Path:
    _PACKAGED_TEMPLATES_FOLDER.mkdir(exist_ok=True)
    return _PACKAGED_TEMPLATES_FOLDER / name


def _force_list(items, item_type: t.Union[t.Type, t.Tuple[t.Type, ...]]):
    if items is None:
        items = []
    elif isinstance(items, item_type):
        items = [items]
    return items


def _to_template_fspath(template_name, template_path) -> str:
    if (template_name is None) == (template_path is None):
        raise ValueError("exactly one of template_name and template_path must be None")
    if template_name is None:
        template_fspath = os.fspath(template_path)
    else:
        template_fspath = os.fspath(template_source_path(template_name))
    return template_fspath


class CloudFormationService:
    """
    Wrapper around the boto3 CloudFormation service resource
    """

    aws_session: boto3.session.Session
    cloudformation_service: boto3.resources.base.ServiceResource
    client: botocore.client.BaseClient

    def __init__(self, aws_session: boto3.session.Session) -> None:
        self.aws_session = aws_session
        self.cloudformation_service = aws_session.resource("cloudformation")
        self.client = self.cloudformation_service.meta.client

    @property
    def profile_name(self) -> t.Optional[str]:
        return self.aws_session.profile_name

    @property
    def region_name(self) -> str:
        return self.aws_session.region_name

    def _get_waiter(self, waiter_name: str) -> botocore.waiter.Waiter:
        return self.client.get_waiter(waiter_name)

    def create_stack(
        self,
        stack_name: str,
        template_name: str = None,
        template_path: t.Union[str, os.PathLike] = None,
        parameters: t.Union[Parameter, t.Collection[Parameter]] = None,
        capabilities: t.Union[str, t.Collection[str]] = None,
        waiter_delay: int = 30,
        waiter_max_attempts: int = 120,
    ) -> t.Mapping[str, t.Any]:
        """
        Create the specified stack, block until it's complete, and return the stack's output.

        You must specify either `template_name` or `template_path`.

        :param stack_name: name assigned to the stack created
        :param template_name: name of the template file in the project's cloudformation directory
        :param template_path: path to the template file
        :param parameters: the stack's input parameters
        :param capabilities: Capabilities delegated to CloudFormation when creating the stack
        :param waiter_delay: polling interval (in seconds) when waiting for the stack creation to complete
        :param waiter_max_attempts: maximum number of polling attempts
        :return: mapping of the output parameter names to their values
        """
        template_fspath = _to_template_fspath(template_name, template_path)
        template_body = _read_file(template_fspath)

        _log.info(f"creating stack {stack_name} in {self.region_name}")
        # noinspection PyUnresolvedReferences
        stack = self.cloudformation_service.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=list(
                map(Parameter.to_input_json, _force_list(parameters, Parameter))
            ),
            Capabilities=_force_list(capabilities, str),
            OnFailure="ROLLBACK",
        )
        _log.info(f"waiting for the creation of stack {stack_name} to complete")
        self._get_waiter("stack_create_complete").wait(
            StackName=stack.stack_id,
            WaiterConfig=dict(Delay=waiter_delay, MaxAttempts=waiter_max_attempts),
        )
        stack.reload()
        output = dict(
            map(lambda o: (o.get("OutputKey"), o.get("OutputValue")), stack.outputs)
        )
        _log.info(f"creation of stack {stack_name} is complete")
        _log.debug(f"stack {stack_name} output:\n{pprint.pformat(output, indent=4)}")
        return output


class SAM(CloudFormationService):
    package_bucket: str

    def __init__(self, aws_session: boto3.session.Session, package_bucket: str):
        super().__init__(aws_session)
        self.package_bucket = package_bucket

    def build(
        self,
        template_name: str = None,
        template_path: t.Union[str, os.PathLike] = None,
        parameters: t.Union[None, Parameter, t.Collection[Parameter]] = None,
        use_container: bool = False,
        debug: bool = False,
    ) -> None:
        template_fspath = _to_template_fspath(template_name, template_path)

        cmd = [
            "sam",
            "build",
            "--base-dir",
            os.fspath(_PROJECT_ROOT),
            "--template",
            template_fspath,
        ]
        if parameters:
            cmd.extend(
                [
                    "--parameter-overrides",
                    " ".join(
                        f"ParameterKey={p.name},ParameterValue={p.value}"
                        for p in _force_list(parameters, Parameter)
                    ),
                ]
            )
        if use_container:
            cmd.append("--use-container")
        if debug:
            cmd.append("--debug")
        profile = self.profile_name
        if profile:
            cmd.extend(["--profile", profile])
        cmd.extend(["--region", self.region_name])
        _log.info(
            "building SAM application:\n  %s", " ".join(f"'{tok}'" for tok in cmd)
        )
        subprocess.run(cmd, check=True)
        _log.info("sam build is complete")

    def package(
        self,
        template_name: str = None,
        template_path: t.Union[str, os.PathLike] = None,
        debug: bool = False,
    ) -> pathlib.Path:
        source_template_name = pathlib.Path(
            _to_template_fspath(template_name, template_path)
        ).name
        output_template_path = packaged_template_path(source_template_name)
        packaged_template_fspath = os.fspath(output_template_path)
        cmd = [
            "sam",
            "package",
            "--s3-bucket",
            self.package_bucket,
            "--output-template-file",
            packaged_template_fspath,
        ]
        if debug:
            cmd.append("--debug")
        profile = self.profile_name
        if profile:
            cmd.extend(["--profile", profile])
        cmd.extend(["--region", self.region_name])
        _log.info(
            "packaging SAM application:\n  %s", " ".join(f"'{tok}'" for tok in cmd)
        )
        subprocess.run(cmd, check=True)
        _log.info("sam package is complete")
        return output_template_path

    def create_stack(
        self,
        stack_name: str,
        template_name: str = None,
        template_path: t.Union[str, os.PathLike] = None,
        parameters: t.Union[Parameter, t.Collection[Parameter]] = None,
        capabilities: t.Union[str, t.Collection[str]] = None,
        waiter_delay: int = 30,
        waiter_max_attempts: int = 120,
        use_container: bool = False,
    ) -> t.Mapping[str, t.Any]:
        debug = _log.isEnabledFor(logging.DEBUG)
        self.build(
            template_name,
            template_path,
            parameters=parameters,
            use_container=use_container,
            debug=debug,
        )
        packaged_template_path = self.package(template_name, template_path, debug=debug)
        return super().create_stack(
            stack_name,
            template_name=None,
            template_path=packaged_template_path,
            parameters=parameters,
            capabilities=capabilities,
            waiter_delay=waiter_delay,
            waiter_max_attempts=waiter_max_attempts,
        )

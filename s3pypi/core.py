import email
import logging
import re
from contextlib import suppress
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

import boto3

from s3pypi import __prog__
from s3pypi.exceptions import S3PyPiError
from s3pypi.index import Hash
from s3pypi.locking import DummyLocker, DynamoDBLocker
from s3pypi.storage import S3Storage

log = logging.getLogger(__prog__)

PackageMetadata = email.message.Message


@dataclass
class Distribution:
    name: str
    version: str
    local_path: Path


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def upload_packages(
    dist: List[Path],
    bucket: str,
    force: bool = False,
    lock_indexes: bool = False,
    put_root_index: bool = False,
    profile: Optional[str] = None,
    region: Optional[str] = None,
    **kwargs,
):
    session = boto3.Session(profile_name=profile, region_name=region)
    storage = S3Storage(session, bucket, **kwargs)
    lock = (
        DynamoDBLocker(session, table=f"{bucket}-locks")
        if lock_indexes
        else DummyLocker()
    )

    distributions = parse_distributions(dist)
    get_name = attrgetter("name")

    for name, group in groupby(sorted(distributions, key=get_name), get_name):
        directory = normalize_package_name(name)
        with lock(directory):
            index = storage.get_index(directory)

            for distr in group:
                filename = distr.local_path.name

                if not force and filename in index.filenames:
                    msg = "%s already exists! (use --force to overwrite)"
                    log.warning(msg, filename)
                else:
                    log.info("Uploading %s", distr.local_path)
                    storage.put_distribution(directory, distr.local_path)
                    index.filenames[filename] = Hash.of("sha256", distr.local_path)

            storage.put_index(directory, index)

    if put_root_index:
        with lock(storage.root):
            index = storage.build_root_index()
            storage.put_index(storage.root, index)


def parse_distribution(path: Path) -> Distribution:
    extensions = (".whl", ".tar.gz", ".tar.bz2", ".tar.xz", ".zip")

    ext = next((ext for ext in extensions if path.name.endswith(ext)), "")
    if not ext:
        raise S3PyPiError(f"Unknown file type: {path}")

    if ext == ".whl":
        meta = extract_wheel_metadata(path)
        name, version = meta["Name"], meta["Version"]
    else:
        name, version = path.name[: -len(ext)].rsplit("-", 1)

    return Distribution(name, version, path)


def parse_distributions(paths: List[Path]) -> List[Distribution]:
    dists = []
    for path in paths:
        if path.is_file():
            dists.append(parse_distribution(path))
        elif not path.exists():
            expanded_paths = Path(".").glob(str(path))
            for expanded_path in (f for f in expanded_paths if f.is_file()):
                with suppress(S3PyPiError):
                    dists.append(parse_distribution(expanded_path))
    return dists


def extract_wheel_metadata(path: Path) -> PackageMetadata:
    with ZipFile(path, "r") as whl:
        try:
            text = next(
                whl.open(fname).read().decode()
                for fname in whl.namelist()
                if fname.endswith("METADATA")
            )
        except StopIteration:
            raise S3PyPiError(f"No wheel metadata found in {path}") from None

    return email.message_from_string(text)

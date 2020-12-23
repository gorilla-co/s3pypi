import email
import logging
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path
from typing import Iterator, List
from zipfile import ZipFile

from s3pypi import __prog__
from s3pypi.exceptions import S3PyPiError
from s3pypi.storage import S3Storage

log = logging.getLogger(__prog__)


@dataclass
class Distribution:
    name: str
    version: str
    local_path: Path


def upload_packages(dist: List[Path], bucket: str, force: bool = False, **kwargs):
    storage = S3Storage(bucket, **kwargs)

    distributions = parse_distributions(dist)
    get_name = attrgetter("name")

    for name, group in groupby(sorted(distributions, key=get_name), get_name):
        directory = storage.directory(name)
        index = storage.get_index(directory)

        for distr in group:
            filename = distr.local_path.name

            if not force and filename in index.filenames:
                log.warning("%s already exists! (use --force to overwrite)", filename)
            else:
                log.info("Uploading %s", distr.local_path)
                storage.put_distribution(directory, distr.local_path)
                index.filenames.add(filename)

        storage.put_index(directory, index)


def parse_distributions(paths: List[Path]) -> Iterator[Distribution]:
    for path in paths:
        if path.name.endswith(".tar.gz"):
            name, version = path.name[:-7].rsplit("-", 1)
        elif path.suffix == ".whl":
            meta = extract_wheel_metadata(path)
            name, version = meta["Name"], meta["Version"]
        else:
            raise S3PyPiError(f"Unknown file type: {path}")

        yield Distribution(name, version, path)


PackageMetadata = email.message.Message


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

import logging
import re
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path
from typing import Iterator, List, Tuple
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
            metadata = extract_wheel_metadata(path)
            name, version = find_wheel_name_and_version(metadata)
        else:
            raise S3PyPiError(f"Unknown file type: {path}")

        yield Distribution(name, version, path)


def extract_wheel_metadata(path: Path) -> str:
    with ZipFile(path, "r") as whl:
        try:
            return next(
                whl.open(fname).read().decode()
                for fname in whl.namelist()
                if fname.endswith("METADATA")
            )
        except StopIteration:
            raise S3PyPiError(f"No wheel metadata found in {path}") from None


def find_wheel_name_and_version(metadata: str) -> Tuple[str, str]:
    name = re.search(r"^Name: (.*)", metadata, flags=re.MULTILINE)
    version = re.search(r"^Version: (.*)", metadata, flags=re.MULTILINE)

    if not (name and version):
        raise S3PyPiError(f"Wheel name and version not found in metadata: {metadata}")

    return name[1], version[1]

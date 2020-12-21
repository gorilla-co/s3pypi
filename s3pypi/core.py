import logging
import re
from collections import defaultdict
from itertools import groupby
from operator import attrgetter
from pathlib import Path
from typing import Iterator, List, Tuple
from zipfile import ZipFile

from s3pypi.exceptions import S3PyPiError
from s3pypi.index import Package
from s3pypi.storage import S3Storage

log = logging.getLogger()


def upload_packages(dist: List[Path], bucket: str, force: bool = False, **kwargs):
    storage = S3Storage(bucket, **kwargs)

    group_key = attrgetter("name")
    packages = sorted(discover_packages(dist), key=group_key)

    for _, group in groupby(packages, group_key):
        versions = list(group)
        index = storage.get_index(versions[0])

        for package in versions:
            index.add_package(package, force)
            storage.put_package(package)

        storage.put_index(index)


def discover_packages(paths: List[Path]) -> Iterator[Package]:
    pkg_files = defaultdict(set)

    for path in paths:
        if path.name.endswith(".tar.gz"):
            name, version = path.name[:-7].rsplit("-", 1)
        elif path.suffix == ".whl":
            metadata = extract_wheel_metadata(path)
            name, version = find_wheel_name_and_version(metadata)
        else:
            raise S3PyPiError(f"Unrecognized file type: {path}")

        pkg_files[(name, version)].add(path)

    for (name, version), files in pkg_files.items():
        files_str = ", ".join(str(f) for f in sorted(files))
        log.info("Package %s %s: %s", name, version, files_str)

        yield Package(name, version, files)


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

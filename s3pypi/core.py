import email
import logging
import re
from contextlib import suppress
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path
from typing import List
from zipfile import ZipFile

from s3pypi import __prog__
from s3pypi.exceptions import S3PyPiError
from s3pypi.index import Hash
from s3pypi.storage import S3Config, S3Storage

log = logging.getLogger(__prog__)

PackageMetadata = email.message.Message


@dataclass
class Config:
    s3: S3Config


@dataclass
class Distribution:
    name: str
    version: str
    local_path: Path


def normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def upload_packages(
    cfg: Config,
    dist: List[Path],
    put_root_index: bool = False,
    strict: bool = False,
    force: bool = False,
) -> None:
    storage = S3Storage(cfg.s3)
    distributions = parse_distributions(dist)

    get_name = attrgetter("name")
    existing_files = []

    for name, group in groupby(sorted(distributions, key=get_name), get_name):
        directory = normalize_package_name(name)

        with storage.locked_index(directory) as index:
            for distr in group:
                filename = distr.local_path.name

                if not force and filename in index.filenames:
                    existing_files.append(filename)
                    msg = "%s already exists! (use --force to overwrite)"
                    log.warning(msg, filename)
                else:
                    log.info("Uploading %s", distr.local_path)
                    storage.put_distribution(directory, distr.local_path)
                    index.filenames[filename] = Hash.of("sha256", distr.local_path)

    if put_root_index:
        with storage.locked_index(storage.root) as root_index:
            root_index.filenames = dict.fromkeys(storage.list_directories())

    if strict and existing_files:
        raise S3PyPiError(f"Found {len(existing_files)} existing files on S3")


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
            new_dists = []
            expanded_paths = Path(".").glob(str(path))
            for expanded_path in (f for f in expanded_paths if f.is_file()):
                with suppress(S3PyPiError):
                    new_dists.append(parse_distribution(expanded_path))
            if not new_dists:
                raise S3PyPiError(f"No valid files found matching: {path}")
            dists.extend(new_dists)
        else:
            raise S3PyPiError(f"Not a file: {path}")
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


def delete_package(cfg: Config, name: str, version: str) -> None:
    storage = S3Storage(cfg.s3)
    directory = normalize_package_name(name)

    with storage.locked_index(directory) as index:
        filenames = [f for f in index.filenames if f.split("-", 2)[1] == version]
        if not filenames:
            raise S3PyPiError(f"Package not found: {name} {version}")

        for filename in filenames:
            log.info("Deleting %s", filename)
            storage.delete(directory, filename)
            del index.filenames[filename]

    if not index.filenames:
        with storage.locked_index(storage.root) as root_index:
            root_index.filenames.pop(directory, None)

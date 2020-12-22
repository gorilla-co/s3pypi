import logging
import re
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent
from typing import Set

from s3pypi.exceptions import S3PyPiError

log = logging.getLogger()


@dataclass(eq=True, frozen=True)
class Package:
    name: str
    version: str
    files: Set[Path] = field(compare=False, default_factory=set)

    def __str__(self):
        return f"{self.name}-{self.version}"

    @property
    def directory(self) -> str:
        return re.sub(r"[-_.]+", "-", self.name.lower())


@dataclass
class Index:
    packages: Set[Package] = field(default_factory=set)

    @classmethod
    def parse(cls, html: str) -> "Index":
        pkg_files = defaultdict(set)

        for match in re.findall(
            r'<a href=".+">((.+?)-(((?:\d+!)?\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.post\d+)?'
            + r"(?:\.dev\d+)?)(?:\+([a-zA-Z0-9\.]+))?).*(?:\.whl|\.tar\.gz))</a>",
            html,
        ):
            pkg_files[(match[1], match[2])].add(Path(match[0]))

        packages = {
            Package(name, version, files)
            for (name, version), files in pkg_files.items()
        }
        return cls(packages)

    def to_html(self) -> str:
        links = "<br>\n".join(
            f'<a href="{urllib.parse.quote(path.name)}">{path.name}</a>'
            for pkg in sorted(self.packages, key=lambda pkg: pkg.version)
            for path in sorted(pkg.files)
        )
        return index_html.format(body=indent(links, " " * 4))

    def add_package(self, package: Package, force: bool = False):
        existing = next(
            (p for p in self.packages if p.version == package.version), None
        )
        if existing:
            a = {f.name for f in existing.files}
            b = {f.name for f in package.files}
            conflicts = a.intersection(b)

            if conflicts and not force:
                raise S3PyPiError(
                    f"{package} already exists in the index: {', '.join(sorted(conflicts))}\n"
                    "Use a different version, or use --force to overwrite existing files."
                )

            if conflicts:
                drop = {f for f in existing.files if f.name in conflicts}
                existing.files.difference_update(drop)
            existing.files.update(package.files)
        else:
            self.packages.add(package)


index_html = """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>Package Index</title>
  </head>
  <body>
{body}
  </body>
</html>
""".strip()

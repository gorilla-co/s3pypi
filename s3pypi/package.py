import logging
import os
import re
import sys
from collections import defaultdict
from subprocess import CalledProcessError, check_output

from jinja2 import Environment, PackageLoader

from s3pypi import __prog__
from s3pypi.exceptions import S3PyPiError

log = logging.getLogger()


class Package(object):
    """Python package."""

    def __init__(self, name, files):
        self.name, self.version = name.rsplit("-", 1)
        self.files = set(files)

    def __str__(self):
        return "%s-%s" % (self.name, self.version)

    def _attrs(self):
        return self.name, self.version

    def __lt__(self, other):
        return self.version < other.version

    def __eq__(self, other):
        return isinstance(other, Package) and self._attrs() == other._attrs()

    def __hash__(self):
        return hash(self._attrs())

    @property
    def directory(self):
        return re.sub(r"[-_.]+", "-", self.name.lower())

    @staticmethod
    def _find_package_name(text):
        match = re.search(
            r"^(copying files to|making hard links in) (.+)\.\.\.",
            text,
            flags=re.MULTILINE,
        )

        if not match:
            raise RuntimeError("Package name not found! (use --verbose to view output)")

        return match.group(2)

    @staticmethod
    def _find_wheel_name(text):
        match = re.search(
            r"creating '.*?(dist.*\.whl)' and adding", text, flags=re.MULTILINE
        )

        if not match:
            raise RuntimeError("Wheel name not found! (use --verbose to view output)")

        return match.group(1)

    @staticmethod
    def create(wheel=True, sdist=True, dist_path=None):
        files = []
        if not dist_path:
            cmd = [sys.executable, "setup.py", "sdist", "--formats", "gztar"]

            if wheel:
                cmd.append("bdist_wheel")

            log.debug("Package create command line: {}".format(" ".join(cmd)))

            try:
                stdout = check_output(cmd).decode().strip()
            except CalledProcessError as e:
                raise RuntimeError(e.output.rstrip())

            log.debug(stdout)

            name = Package._find_package_name(stdout)

            if sdist:
                files.append(name + ".tar.gz")

            if wheel:
                files.append(os.path.basename(Package._find_wheel_name(stdout)))
        else:
            for f in os.listdir(dist_path):
                if f.endswith(".tar.gz"):
                    name = f[:-7]
                files.append(f)

        log.debug("Package name: {}".format(name))
        log.debug("Files to upload: {}".format(files))

        return Package(name, files)


class Index(object):
    """Index of package versions, to be rendered to HTML."""

    template = Environment(loader=PackageLoader(__prog__, "templates")).get_template(
        "index.html.j2"
    )

    def __init__(self, packages):
        self.packages = set(packages)

    @staticmethod
    def parse(html):
        filenames = defaultdict(set)

        for match in re.findall(
            r'<a href=".+">((.+?-((?:\d+!)?\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.post\d+)?'
            + r"(?:\.dev\d+)?)(?:\+([a-zA-Z0-9\.]+))?).*(?:\.whl|\.tar\.gz))</a>",
            html,
        ):
            filenames[match[1]].add(match[0])

        return Index(Package(name, files) for name, files in filenames.items())

    def to_html(self):
        return self.template.render({"packages": self.packages})

    def add_package(self, package, force=False):
        if force:
            self.packages.discard(package)
        elif any(p.version == package.version for p in self.packages):
            raise S3PyPiError(
                "%s already exists! You should use a different version (use --force to override)."
                % package
            )

        self.packages.add(package)

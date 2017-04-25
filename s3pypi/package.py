import glob
import os
import re
from collections import defaultdict
from subprocess import check_output, CalledProcessError

from jinja2 import Environment, PackageLoader

from s3pypi import __prog__
from s3pypi.exceptions import S3PyPiError

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


class Package(object):
    """Python package."""

    def __init__(self, name, files):
        self.name, self.version = name.rsplit('-', 1)
        self.files = set(files)

    def __str__(self):
        return '%s-%s' % (self.name, self.version)

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
        return re.sub('[-_.]+', '-', self.name)

    @staticmethod
    def _find_package_name(text):
        match = re.search('^(copying files to|making hard links in) (.+)\.\.\.', text, flags=re.MULTILINE)

        if not match:
            raise RuntimeError('Package name not found in:\n' + text)

        return match.group(2)

    @staticmethod
    def create(wheel=True):
        cmd = ['python', 'setup.py', 'sdist', '--formats', 'gztar']

        if wheel:
            cmd.append('bdist_wheel')

        try:
            stdout = check_output(cmd).decode().strip()
        except CalledProcessError as e:
            raise RuntimeError(e.output.rstrip())

        name = Package._find_package_name(stdout)
        files = [name + '.tar.gz']

        if wheel:
            files.extend(os.path.basename(path) for path in
                         glob.glob(os.path.join('dist', name + '-*.whl')))

        return Package(name, files)


class Index(object):
    """Index of package versions, to be rendered to HTML."""

    template = Environment(loader=PackageLoader(__prog__, 'templates')).get_template('index.html.j2')

    def __init__(self, packages):
        self.packages = set(packages)

    @staticmethod
    def parse(html):
        filenames = defaultdict(set)

        for match in re.findall('<a href="((.+?-\d+\.\d+\.\d+).+)">', html):
            filenames[match[1]].add(match[0])

        return Index(Package(name, files) for name, files in filenames.items())

    def to_html(self):
        return self.template.render({'packages': self.packages})

    def add_package(self, package, force=False):
        if force:
            self.packages.discard(package)
        elif any(p.version == package.version for p in self.packages):
            raise S3PyPiError('%s already exists! You should use a different version.' % package)

        self.packages.add(package)

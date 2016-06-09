import glob
import os
import re
from collections import defaultdict
from subprocess import check_output, CalledProcessError

from jinja2 import Environment, PackageLoader

from s3pypi import __prog__

__author__ = 'Matteo De Wint'
__copyright__ = 'Copyright 2016, November Five'
__license__ = 'MIT'


class Package(object):
    """Python package archive."""

    def __init__(self, name, files):
        self.name, self.version = name.split('-')
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

    @staticmethod
    def create(wheel=True):
        cmd = ['python', 'setup.py', 'sdist', '--formats', 'gztar']

        if wheel:
            cmd.append('bdist_wheel')

        try:
            stdout = check_output(cmd).strip()
        except CalledProcessError as e:
            raise RuntimeError(e.output.rstrip())

        match = re.search('^making hard links in (.+)\.\.\.$', stdout, flags=re.MULTILINE)

        if not match:
            raise RuntimeError(stdout)

        name = match.group(1)
        files = [name + '.tar.gz']

        if wheel:
            files.extend(os.path.basename(path) for path in
                         glob.glob(os.path.join('dist', name + '-*.whl')))

        return Package(name, files)


class Index(object):
    """Index containing URLs to all versions of a package, to be rendered to HTML."""

    template = Environment(loader=PackageLoader(__prog__, 'templates')).get_template('index.html.j2')

    def __init__(self, url, packages):
        self.packages = set(packages)
        self.url = url

    @staticmethod
    def parse(url, html):
        filenames = defaultdict(set)

        for match in re.findall('<a href=".+/((.+?-\d+\.\d+\.\d+).+)">', html):
            filenames[match[1]].add(match[0])

        return Index(url, (Package(name, files) for name, files in filenames.iteritems()))

    def to_html(self):
        return self.template.render({'url': self.url, 'packages': self.packages})

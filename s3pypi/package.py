import re
from subprocess import check_output, CalledProcessError

from jinja2 import Environment, PackageLoader

from s3pypi import __prog__


class Package(object):

    def __init__(self, name):
        self.name, self.version = name.split('-')
        self.filename = '%s.tar.gz' % name

    def __str__(self):
        return '%s-%s' % (self.name, self.version)

    def _attrs(self):
        return self.name, self.version, self.filename

    def __lt__(self, other):
        return self.version < other.version

    def __eq__(self, other):
        return isinstance(other, Package) and self._attrs() == other._attrs()

    def __hash__(self):
        return hash(self._attrs())

    @staticmethod
    def create():
        try:
            stdout = check_output(['python', 'setup.py', 'sdist', '--formats', 'gztar']).strip()
        except CalledProcessError as e:
            raise RuntimeError(e.output.rstrip())

        match = re.search('^making hard links in (.+)\.\.\.$', stdout, flags=re.MULTILINE)

        if match:
            return Package(match.group(1))
        else:
            raise RuntimeError(stdout)


class Index(object):

    template = Environment(loader=PackageLoader(__prog__, 'templates')).get_template('index.html.j2')

    def __init__(self, url, packages):
        self.packages = set(packages)
        self.url = url

    @staticmethod
    def parse(url, html):
        return Index(url, (Package(m[1]) for m in re.findall('<a href="(.+)">(.+)</a>', html)))

    def to_html(self):
        return self.template.render({'url': self.url, 'packages': sorted(self.packages, reverse=True)})

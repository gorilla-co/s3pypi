import re
import urllib.parse
from dataclasses import dataclass, field
from textwrap import indent
from typing import Dict, Optional


@dataclass(frozen=True)
class Filename:
    name: str
    hash_name: Optional[str] = None
    hash_value: Optional[str] = None

    @property
    def url_path(self):
        path = urllib.parse.quote(self.name)
        if not self.hash_value:
            return path
        return f"{path}#{self.hash_name}={self.hash_value}"

    def __str__(self):
        return self.name


@dataclass
class Index:
    filenames: Dict[str, Filename] = field(default_factory=dict)

    @classmethod
    def parse(cls, html: str) -> "Index":
        matches = re.findall(r'<a href=".+?((\w+)=(\w+))?">(.+)</a>', html)
        filenames = {
            name: Filename(name, hash_name or None, hash_value or None)
            for _, hash_name, hash_value, name in matches
        }
        return cls(filenames)

    def put(self, filename: Filename):
        self.filenames[filename.name] = filename

    def to_html(self) -> str:
        links = "<br>\n".join(
            f'<a href="{f.url_path}">{f.name.rstrip("/")}</a>'
            for f in sorted(self.filenames.values(), key=lambda f: f.name)
        )
        return index_html.format(body=indent(links, " " * 4))


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

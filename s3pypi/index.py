import re
import urllib.parse
from dataclasses import dataclass, field
from textwrap import indent
from typing import Set


@dataclass
class Index:
    filenames: Set[str] = field(default_factory=set)

    @classmethod
    def parse(cls, html: str) -> "Index":
        filenames = set(re.findall(r'<a href=".+">(.+)</a>', html))
        return cls(filenames)

    def to_html(self) -> str:
        links = "<br>\n".join(
            f'<a href="{urllib.parse.quote(fname)}">{fname.rstrip("/")}</a>'
            for fname in sorted(self.filenames)
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

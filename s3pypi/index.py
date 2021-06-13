from __future__ import annotations

import hashlib
import re
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import indent
from typing import Dict, Optional


@dataclass
class Hash:
    name: str
    value: str

    @classmethod
    def of(cls, name: str, path: Path) -> Hash:
        h = hashlib.new(name)
        with open(path, "rb") as file:
            while True:
                block = file.read(65536)
                if not block:
                    break
                h.update(block)
        return cls(name, h.hexdigest())


@dataclass
class Index:
    filenames: Dict[str, Optional[Hash]] = field(default_factory=dict)

    @classmethod
    def parse(cls, html: str) -> Index:
        matches = re.findall(r'<a href=".+?((\w+)=(\w+))?">(.+)</a>', html)
        filenames = {
            fname: Hash(hash_name, hash_value) if hash_name else None
            for _, hash_name, hash_value, fname in matches
        }
        return cls(filenames)

    def to_html(self) -> str:
        links = "<br>\n".join(
            f'<a href="{urllib.parse.quote(fname)}'
            + (f"#{hash_.name}={hash_.value}" if hash_ else "")
            + f'">{fname.rstrip("/")}</a>'
            for fname, hash_ in sorted(self.filenames.items())
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

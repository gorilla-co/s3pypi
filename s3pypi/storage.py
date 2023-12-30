from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import boto3
import botocore
from botocore.config import Config

from s3pypi.index import Index


@dataclass
class S3Config:
    bucket: str
    prefix: Optional[str] = None
    endpoint_url: Optional[str] = None
    put_kwargs: dict = field(default_factory=dict)
    unsafe_s3_website: bool = False
    no_sign_request: bool = False


class S3Storage:
    root = "/"
    _index = "index.html"

    def __init__(self, session: boto3.session.Session, cfg: S3Config):
        _config = None
        if cfg.no_sign_request:
            _config = Config(signature_version=botocore.session.UNSIGNED)

        self.s3 = session.resource("s3", endpoint_url=cfg.endpoint_url, config=_config)
        self.index_name = self._index if cfg.unsafe_s3_website else ""
        self.cfg = cfg

    def _object(self, directory: str, filename: str):
        parts = [directory, filename]
        if parts == [self.root, self.index_name]:
            parts = [self._index]
        if self.cfg.prefix:
            parts.insert(0, self.cfg.prefix)
        return self.s3.Object(self.cfg.bucket, key="/".join(parts))

    def get_index(self, directory: str) -> Index:
        try:
            html = self._object(directory, self.index_name).get()["Body"].read()
        except botocore.exceptions.ClientError:
            return Index()
        return Index.parse(html.decode())

    def build_root_index(self) -> Index:
        paginator = self.s3.meta.client.get_paginator("list_objects_v2")
        result = paginator.paginate(
            Bucket=self.cfg.bucket,
            Prefix=self.cfg.prefix or "",
            Delimiter="/",
        )
        n = len(self.cfg.prefix) + 1 if self.cfg.prefix else 0
        dirs = (p.get("Prefix")[n:] for p in result.search("CommonPrefixes"))
        return Index(dict.fromkeys(dirs))

    def put_index(self, directory: str, index: Index):
        self._object(directory, self.index_name).put(
            Body=index.to_html(),
            ContentType="text/html",
            CacheControl="public, must-revalidate, proxy-revalidate, max-age=0",
            **self.cfg.put_kwargs,
        )

    def put_distribution(self, directory: str, local_path: Path):
        with open(local_path, mode="rb") as f:
            self._object(directory, local_path.name).put(
                Body=f,
                ContentType="application/x-gzip",
                **self.cfg.put_kwargs,
            )

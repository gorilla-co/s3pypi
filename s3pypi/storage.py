from pathlib import Path
from typing import Optional

import boto3
import botocore

from s3pypi.index import Index


class S3Storage:
    root = "/"
    _index = "index.html"

    def __init__(
        self,
        session: boto3.session.Session,
        bucket: str,
        prefix: Optional[str] = None,
        acl: Optional[str] = None,
        s3_put_args: Optional[dict] = None,
        unsafe_s3_website: bool = False,
    ):
        self.s3 = session.resource("s3")
        self.bucket = bucket
        self.prefix = prefix
        self.index_name = self._index if unsafe_s3_website else ""
        self.put_kwargs = dict(
            ACL=acl or "private",
            **(s3_put_args or {}),
        )

    def _object(self, directory: str, filename: str):
        parts = [directory, filename]
        if parts == [self.root, self.index_name]:
            parts = [self._index]
        if self.prefix:
            parts.insert(0, self.prefix)
        return self.s3.Object(self.bucket, key="/".join(parts))

    def get_index(self, directory: str) -> Index:
        try:
            html = self._object(directory, self.index_name).get()["Body"].read()
        except botocore.exceptions.ClientError:
            return Index()
        return Index.parse(html.decode())

    def build_root_index(self) -> Index:
        paginator = self.s3.meta.client.get_paginator("list_objects_v2")
        result = paginator.paginate(
            Bucket=self.bucket,
            Prefix=self.prefix or "",
            Delimiter="/",
        )
        n = len(self.prefix) + 1 if self.prefix else 0
        dirs = set(p.get("Prefix")[n:] for p in result.search("CommonPrefixes"))
        return Index(dirs)

    def put_index(self, directory: str, index: Index):
        self._object(directory, self.index_name).put(
            Body=index.to_html(),
            ContentType="text/html",
            CacheControl="public, must-revalidate, proxy-revalidate, max-age=0",
            **self.put_kwargs,
        )

    def put_distribution(self, directory: str, local_path: Path):
        with open(local_path, mode="rb") as f:
            self._object(directory, local_path.name).put(
                Body=f,
                ContentType="application/x-gzip",
                **self.put_kwargs,
            )

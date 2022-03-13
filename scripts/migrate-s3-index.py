#!/usr/bin/env python
import argparse

import boto3


def confirm(prompt: str, accepted_answer: str = "yes") -> bool:
    answer = input(
        f"{prompt}\n"
        f"Only '{accepted_answer}' will be accepted to confirm.\n\n"
        "Enter a value: "
    )
    return answer == accepted_answer


def rename_index_html_objects(bucket: str):
    s3 = boto3.client("s3")
    INDEX_HTML = "/index.html"

    indexes = [
        obj["Key"]
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket)
        for obj in page["Contents"]
        if obj["Key"].endswith(INDEX_HTML)
    ]
    if not indexes:
        print(f"No `*{INDEX_HTML}` objects found. Nothing to migrate.")
        return

    to_rename = [(key, key.replace(INDEX_HTML, "/")) for key in indexes]

    print(f"{len(to_rename)} objects will be renamed:")
    for src_key, dst_key in to_rename:
        print(f"  {src_key} -> {dst_key}")

    if confirm("\nRename the objects listed above?"):
        print("\nRenaming...")
        for src_key, dst_key in to_rename:
            print(f"  {src_key} -> {dst_key}")
            src_obj = dict(Bucket=bucket, Key=src_key)
            s3.copy_object(
                CopySource=src_obj,
                Bucket=bucket,
                Key=dst_key,
            )
            s3.delete_object(**src_obj)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bucket", help="S3 bucket name")
    args = p.parse_args()

    rename_index_html_objects(args.bucket)


if __name__ == "__main__":
    main()

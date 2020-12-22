# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## Unreleased

### Added

- Terraform configuration for S3 and CloudFront, including optional **basic
  authentication** using Lambda@Edge and AWS Systems Manager Parameter Store.
  Existing resources created using the old CloudFormation templates can be
  [imported into Terraform](https://www.terraform.io/docs/import/index.html).

### Changed

- CLI arguments have been overhauled. See `s3pypi --help` for details.
- The **default behaviour for uploading index pages** has changed. Previously,
  they would be placed under the `<package>/index.html` key in S3, which could
  be changed to `<package>/` using the `--bare` option. This has now been
  reversed: the default key is `<package>/`, and an option `--unsafe-s3-website`
  was added to append `index.html`. This new behaviour assumes that CloudFront
  uses the S3 REST API endpoint as its origin, not the S3 website endpoint. This
  allows the bucket to remain private, with CloudFront accessing it through an
  [Origin Access Identity (OAI)]. The new Terraform configuration includes such
  an OAI by default. To keep using the old configuration, packages must be
  uploaded with `--unsafe-s3-website --acl public-read`. This is **not
  recommended**, because the files will be **publicly accessible**!

[Origin Access Identity (OAI)]: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html

### Removed

- **Python 2 support**.
- Automatic creation of distributions. From now on, **distributions must be
  created using a separate build command**. See the [README](README.md) for
  an example.
- The `--private` option. The **default ACL is now** `private`, and you can pass a
  different one using the `--acl` option.
- CloudFormation templates (replaced by Terraform configuration).
- Jinja2 dependency.


## 0.11.0 - 2020-09-01

### Added

- New `--acl` option, mutually exclusive with `--private`.
  [@marcelgwerder](https://github.com/marcelgwerder)


## 0.10.1 - 2020-01-14

### Fixed

- Preserve existing files of the same version in the index when uploading with `--force`.
  [@natefoo](https://github.com/natefoo)


## 0.10.0 - 2019-09-18

### Added

- Support `--dist-path` with only a wheel package present.
  [@takacsd](https://github.com/takacsd)

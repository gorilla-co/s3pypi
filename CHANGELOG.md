# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## Unreleased

### Added

- Terraform configuration for S3 and CloudFront.

### Removed

- Dropped Python 2 support.
- CloudFormation templates (replaced by Terraform configuration).


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

# How to contribute

## Getting started

This file describes all the different ways in which you can contribute.


## Reporting a bug

Have you encountered a bug? Please let us know by reporting it.

Before doing so, take a look at the existing [Issues] to make sure the bug you
encountered hasn't already been reported by someone else. If so, we ask you to
reply to the existing Issue rather than creating a new one. Bugs with many
replies will obviously have a higher priority.

If the bug you encountered has not been reported yet, create a new Issue for it
and make sure to label it as a 'bug'. To allow us to help you as efficiently as
possible, always try to include the following:

- Which version of s3pypi are you using?
- Which operating system or environment did the bug occur on?
- What went wrong?
- What did you expect to happen?
- Detailed steps to reproduce.

The maintainer of this repository monitors issues on a regular basis and will
respond to your bug report as soon as possible.

A clear bug report with steps to reproduce is the most helpful contribution you
can make. You don't need to send a fix along with it.


## Requesting an enhancement

Do you have a great idea that could make s3pypi even better? First take a look
at the **Roadmap** section of our [README](README.md), maybe it is already
planned for a future update. If not, feel free to request an enhancement.

Before doing so, take a look at the existing [Issues] to make sure your idea
hasn't already been requested by someone else. If so, we ask you to reply or
give a thumbs-up to the existing Issue rather than creating a new one. Requests
with many replies will obviously have a higher priority.

If your idea has not been requested yet, create a new Issue for it and make sure
to label it as an 'enhancement'. Explain what your idea is in detail and how it
could improve s3pypi.

The maintainer of this repository monitors issues on a regular basis and will
respond to your request as soon as possible.


## Contributing code

s3pypi is maintained in limited spare time, and reviewing a pull request often
takes more effort than making the change. Code contributions are most welcome
from people who use s3pypi and want to improve it for their own use case.

**Open an issue before writing any code**, including for small bug fixes.
Describe the problem, how you use s3pypi, and how you ran into it. The
maintainer may choose to fix it directly. Only open a pull request once the
maintainer has agreed to one.

Pull requests without such an issue may be closed without review, as may changes
produced by automated tools. If you don't use s3pypi yourself, please don't open
pull requests for it. If you found a problem by reading the code, report it in
an issue instead.

The workflow for creating a pull request:

1. Open an issue and wait for the maintainer to agree to a pull request.
2. Fork the repository.
3. `clone` your forked repository.
4. Create a new feature branch from the `master` branch.
5. Make your contributions to the project's code. Please follow the project's
   style guide (listed below), and run the tests before committing.
6. Add documentation where required.
7. Add your changes to the [changelog](CHANGELOG.md) in the "Unreleased"
   section. The maintainer decides when to create a new release.
8. `commit` your changes in logical chunks.
9. `push` your branch to your fork on GitHub.
10. Create a pull request from your feature branch to the original repository's
    `master` branch, and link the issue in its description, e.g. "Fixes #123".

The maintainer of this repository monitors pull requests on a regular basis and
will respond as soon as possible. The smaller individual pull requests are, the
faster the maintainer will be able to respond.


### Local development

Install the project's dependencies, and make sure that all tests pass:

```bash
make install
make test
```

Run the s3pypi CLI:

```bash
poetry run s3pypi
```

This project uses the [Black](https://github.com/psf/black) code style. When
contributing code, please format your changes accordingly.

Check for lint & formatting errors:

```bash
make lint
```

Reformat all source files:

```bash
make format
```


## Contact

Discussions about s3pypi take place on this repository's [Issues] and [Pull
Requests] sections. Anybody is welcome to join the conversation. Wherever
possible, do not take these conversations to private channels, including
contacting the maintainers directly. Keeping communication public means
everybody can benefit and learn.


[Issues]: https://github.com/gorilla-co/s3pypi/issues
[Pull Requests]: https://github.com/gorilla-co/s3pypi/pulls

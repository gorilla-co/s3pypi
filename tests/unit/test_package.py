from s3pypi.package import Package


def test_find_package_name(sdist_output):
    stdout, expected_name = sdist_output
    assert Package._find_package_name(stdout) == expected_name

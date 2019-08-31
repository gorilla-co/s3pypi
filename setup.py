from setuptools import setup, find_packages

import s3pypi.admin
import s3pypi.infrastructure

setup(
    name='s3pypi-auth',
    version=s3pypi.__version__,

    description='CLI tool for creating a Python Package Repository in an S3 bucket',

    author='Ruben Van den Bossche, Matteo De Wint',
    author_email='ruben@novemberfive.co, matteo@novemberfive.co',
    url='https://github.com/novemberfiveco/s3pypi',
    download_url='https://github.com/novemberfiveco/s3pypi/tarball/' + s3pypi.__version__,

    packages=find_packages(exclude=('s3pypi_auth', )),
    package_data={s3pypi.__prog__: ['templates/*.j2']},

    install_requires=['basicauth', 'boto3', 'Jinja2>=2.7', 'passlib>=1.7', 'wheel'],
    entry_points={
        'console_scripts': [
            '{0}={0}.__main__:main'.format(s3pypi.__prog__),
            '{0}={1}.__main__:main'.format(s3pypi.admin.__prog__, s3pypi.admin.__package__),
            '{0}={1}.__main__:main'.format(s3pypi.infrastructure.__prog__, s3pypi.infrastructure.__package__)
        ]
    },
)

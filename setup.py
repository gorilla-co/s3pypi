from setuptools import setup, find_packages

from s3pypi import __prog__, __version__


setup(
    name=__prog__,
    version=__version__,

    description='CLI tool for creating a Python Package Repository in an S3 bucket',

    author='Ruben Van den Bossche, Matteo De Wint',
    author_email='ruben@novemberfive.co, matteo@novemberfive.co',
    url='https://github.com/novemberfiveco/s3pypi',
    download_url='https://github.com/novemberfiveco/s3pypi/tarball/' + __version__,

    packages=find_packages(),
    package_data={__prog__: ['templates/*.j2']},

    install_requires=['boto', 'Jinja2', 'wheel'],
    entry_points={'console_scripts': ['{0}={0}.cli:main'.format(__prog__)]},
)

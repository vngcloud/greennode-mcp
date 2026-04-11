#!/usr/bin/env python
import codecs
import os.path
import re

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


install_requires = [
    'httpx>=0.27.0,<1.0',
    'jmespath>=1.0.0,<2.0',
    'colorama>=0.4.0,<0.5',
    'PyYAML>=6.0,<7.0',
]


setup(
    name='grncli',
    version=find_version('grncli', '__init__.py'),
    description='Universal Command Line Interface for Green Node',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    author='Green Node',
    url='https://github.com/vngcloud/greennode-cli',
    project_urls={
        'Documentation': 'https://github.com/vngcloud/greennode-cli#readme',
        'Source': 'https://github.com/vngcloud/greennode-cli',
        'Bug Tracker': 'https://github.com/vngcloud/greennode-cli/issues',
        'Changelog': 'https://github.com/vngcloud/greennode-cli/blob/main/CHANGELOG.md',
    },
    scripts=['bin/grn'],
    packages=find_packages(exclude=['tests*']),
    package_data={'grncli': ['data/*.json']},
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        'dev': [
            'pytest>=8.0',
            'respx>=0.22.0',
            'pytest-asyncio>=0.24.0',
            'build>=1.0',
        ],
    },
    python_requires='>=3.10',
    license='Apache License 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
)

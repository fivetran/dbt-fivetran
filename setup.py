#!/usr/bin/env python
import os
import sys

# require python 3.9 or newer
if sys.version_info < (3, 9):
    print('Error: dbt does not support this version of Python.')
    print('Please upgrade to Python 3.9 or higher.')
    sys.exit(1)

# require version of setuptools that supports find_namespace_packages
from setuptools import setup

try:
    from setuptools import find_namespace_packages
except ImportError:
    # the user has a downlevel version of setuptools.
    print("Error: dbt requires setuptools v40.1.0 or higher.")
    print('Please upgrade setuptools with "pip install --upgrade setuptools" and try again')
    sys.exit(1)

def read(rel_path):
    this_directory = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_directory, rel_path), 'r') as f:
        return f.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('version'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

from pathlib import Path

package_name = "dbt-fivetran"
description = """dbt (data build tool) adapter for Fivetran Datalake"""
README = Path(__file__).parent / "README.md"


setup(
    name=package_name,
    version=get_version("dbt/adapters/fivetran/__version__.py"),
    description=description,
    long_description=README.read_text(),
    long_description_content_type='text/markdown',
    author="Emrah Diril",
    author_email="support@fivetran.com",
    url='https://github.com/fivetran/dbt-fivetran',
    packages=find_namespace_packages(include=["dbt", "dbt.*"]),
    include_package_data=True,
    install_requires=[
        "dbt-common>=1.10,<2.0",
        "dbt-adapters>=1.7,<2.0",
        "dbt-duckdb>=1.8.3",
        "pyarrow>=18.0.0",
        "pyiceberg>=0.8.1",
        "dbt-core>=1.8.0",
    ],
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.9",
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
)

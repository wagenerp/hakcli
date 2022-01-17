#!/usr/bin/env python3
import sys
from setuptools import setup, find_packages

setup(
  name='hakcli',
  author='Peter Wagener',
  version='1.0',
  packages=find_packages(where='src'),
  package_dir={'': 'src'},
  extras_require={},
  install_requires=[],
  url='https://github.com/wagenerp/hakcli',
  maintainer='Peter Wagener',
  maintainer_email='mail@peterwagener.net',
  python_requires='>=3.5',
  classifiers=[
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    "Programming Language :: Python :: 3.10",
  ]
)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from setuptools import setup, find_packages

from fispip import __program__, __version__, __description__

README = open('README.rst').read()

setup(
    name=__program__,
    version=__version__,
    license='MIT',
    description=__description__,
    long_description=README,
    url='https://github.com/fopina/pyfispip',
    download_url='https://github.com/fopina/pyfispip/tarball/v%s' %
    __version__,
    author='Filipe Pina',
    author_email='fopina@skmobi.com',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    keywords=['database', 'gtm', 'mtm', 'pip', 'fis']
)

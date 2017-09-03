#!/usr/bin/env python
# coding=utf-8

import os
from setuptools import setup, find_packages

if os.environ.get('USER', '') == 'vagrant':
    del os.link

version = __import__('tn_parser').__version__

install_requires = [
    'django>=1.10,<1.11',
    'django-environ>=0.4.0,<1.0.0',
    'requests[security]<3',
    'beautifulsoup4',
    'raven<6.1',
]

dev_requires = [
    'django-cors-headers',
    'ipdb',
    'ipython',
    'pytest',
    'pytest-django'
]

setup(
    name='transport_nov_parser',
    version=version,
    description='Transport.nov parser and model presenter',
    author='Ilya Pavlov',
    author_email='',
    url='https://www.python.org/sigs/distutils-sig/',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    install_requires=install_requires,

    extras_require={
        'dev': dev_requires,
        'mysql': [
            'mysqlclient>=1.3.6,<1.4',
        ]
    }
)

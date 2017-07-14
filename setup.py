#!/usr/bin/env python
"""
Zask
----

Zask is a framework for Python based on ZeroRPC, which is a
RPC protocol and implemented in Python.

Zask is mostly inspired by Flask.

Links
`````

* `ZeroRPC <https://github.com/0rpc/zerorpc-python>`

"""
import re
import ast
from setuptools import setup, find_packages


_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('zask/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))


setup(
    name='Zask',
    version=version,
    license='BSD',
    author='J5',
    url='https://github.com/j-5/zask',
    description="Basic framework to use with ZeroRPC inspired by Flask",
    long_description=__doc__,
    packages=find_packages(),
    install_requires=[
        'zerorpc>=0.5.1, <0.7',
        'sqlalchemy>=0.9.8, <1.2'
    ],
    classifiers=[
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ]
)

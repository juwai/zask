#!/usr/bin/env python
"""
Zask
----

Zask is a framework for Python based on ZeroRPC, which is a
RPC protocol and implemented in Python.

Zask is mostly inspired by Flask.

Links
`````

* `ZeroRPC <https://github.com/dotcloud/zerorpc-python>`

"""

from setuptools import setup, find_packages


setup(
    name = 'Zask',
    version = '1.5-dev',
    license='BSD',
    author = 'J5',
    description = "Basic framework to use with ZeroRPC inspired by Flask",
    long_description=__doc__,
    packages = find_packages(),
    install_requires = [
        'zerorpc==0.4.4',
        'sqlalchemy>=0.9.8, <1.0',
        'oursql>=0.9.3, <1.0'
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

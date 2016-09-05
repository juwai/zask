Zask
====

[![Build Status](https://travis-ci.org/juwai/zask.svg?branch=master)](https://travis-ci.org/juwai/zask)

[![Documentation Status](https://readthedocs.org/projects/zask/badge/?version=latest)](https://readthedocs.org/projects/zask/?badge=latest)

Zask is a framework to work with ZeroRPC. Zask is inspired by Flask, you can consider zask is Flask without `WSGI`, `Jinja2` and `Router` but with ZeroRPC and SQLAlchemy.

## Installation

```
$ pip install zask
```

## Tests

```
$ py.test
```

If you have `tox`, then:

```
$ tox
```

## Release

Follow these steps to release on pypi.

* Create ~/.pypirc with this content. Fill in username and password.
```
[distutils]
index-servers =
    pypi

[pypi]
username:<username>
password:<password>
```
* Update [CHANGES](CHANGES) with new version number and describe the changes.
* Set new version number in `zask/__init__.py`
* Run `python bin/release.py`
* Push release tag to Github

## Changes

see [Changes](/CHANGES).

## Credits

see [Authors](/AUTHORS).

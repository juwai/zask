Zask
====

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

1. Create ~/.pypirc with this content. Fill in username and password.
```
[distutils]
index-servers =
    pypi

[pypi]
username:<username>
password:<password>
```
2. Update [CHANGES](CHANGES) with new version number and describe the changes.
3. Set new version number in `zask/__init__.py`
4. Run `python bin/release.py`
5. Push release tag to Github

## Changes

see [Changes](/CHANGES).

## Credits

see [Authors](/AUTHORS).

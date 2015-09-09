# -*- coding: utf-8 -*-
"""
    release
    ~~~~~~~

    Helper script that performs a release.  Does pretty much everything
    automatically for us.

    :copyright: (c) 2014 by the J5.
    :license: BSD, see LICENSE for more details.

    :copyright: (c) 2014 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
import pkg_resources
import sys
import os
import re
from datetime import datetime, date
from subprocess import Popen, PIPE

def get_current_version():
    try:
        release = pkg_resources.get_distribution('Zask').version
    except pkg_resources.DistributionNotFound:
        print 'To build the documentation, The distribution information of Zask'
        print 'Has to be available.  Either install the package into your'
        print 'development environment or run "setup.py develop" to setup the'
        print 'metadata.  A virtualenv is recommended!'
        sys.exit(1)

    if '-dev' in release:
        release = release.split('-dev')[0]

    version = '.'.join(release.split('.')[:2])
    return version

def bump_version(version):
    try:
        parts = map(int, version.split('.'))
    except ValueError:
        fail('Current version is not numeric')
    parts[-1] += 1
    return '.'.join(map(str, parts))


def set_filename_version(filename, version_number, pattern):
    changed = []

    def inject_version(match):
        before, old, after = match.groups()
        changed.append(True)
        return before + version_number + after
    with open(filename) as f:
        contents = re.sub(r"^(\s*%s\s*=\s*')(.+?)(')(?sm)" % pattern,
                          inject_version, f.read())

    if not changed:
        fail('Could not find %s in %s', pattern, filename)

    with open(filename, 'w') as f:
        f.write(contents)


def set_init_version(version):
    info('Setting __init__.py version to %s', version)
    set_filename_version('zask/__init__.py', version, '__version__')


def set_setup_version(version):
    info('Setting setup.py version to %s', version)
    set_filename_version('setup.py', version, 'version')

def fail(message, *args):
    print >> sys.stderr, 'Error:', message % args
    sys.exit(1)

def info(message, *args):
    print >> sys.stderr, message % args


def get_git_tags():
    return set(Popen(['git', 'tag'], stdout=PIPE).communicate()[0].splitlines())


def git_is_clean():
    return Popen(['git', 'diff', '--quiet']).wait() == 0


def make_git_commit(message, *args):
    message = message % args
    Popen(['git', 'commit', '-am', message]).wait()


def make_git_tag(tag):
    info('Tagging "%s"', tag)
    Popen(['git', 'tag', tag]).wait()


def main():
    os.chdir(os.path.join(os.path.dirname(__file__), '..'))

    version = get_current_version()
    dev_version = bump_version(version) + '-dev'

    info('Releasing %s', version)
    tags = get_git_tags()

    if version in tags:
        fail('Version "%s" is already tagged', version)

    if not git_is_clean():
        fail('You have uncommitted changes in git')

    set_init_version(version)
    set_setup_version(version)
    make_git_commit('Bump version number to %s', version)
    make_git_tag(version)
    set_init_version(dev_version)
    set_setup_version(dev_version)


if __name__ == '__main__':
    main()

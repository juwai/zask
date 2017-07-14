import random
import os

_tmpfiles = []


def random_ipc_endpoint():
    tmpfile = '/tmp/zerorpc_test_socket_{0}.sock'.format(
        str(random.random())[2:])
    _tmpfiles.append(tmpfile)
    return 'ipc://{0}'.format(tmpfile)


def teardown():
    global _tmpfiles
    for tmpfile in _tmpfiles:
        print 'unlink', tmpfile
        try:
            os.unlink(tmpfile)
        except Exception:
            pass
    _tmpfiles = []

"""
    tests.logging
    ~~~~~~~~~~~~~

    Logging part just print logs to make sure logging is working.

"""
import os
import time
import unittest
import pytest
import tempfile

import zerorpc
import gevent
from zerorpc.channel import logger as channel_logger
from zerorpc.gevent_zmq import logger as gevent_logger
from zerorpc.core import logger as core_logger
from zask import Zask
from zask.ext.zerorpc import init_zerorpc, access_log
from zask.logging import create_logger


def clear_handlers():
    del channel_logger.handlers[:]
    del gevent_logger.handlers[:]
    del core_logger.handlers[:]


class TestZeroRPC(unittest.TestCase):

    def setUp(self):
        fd1, error_log_path = tempfile.mkstemp()
        fd2, access_log_path = tempfile.mkstemp()
        self.default_config = {
            "DEBUG": True,
            "ERROR_LOG": error_log_path,
            "ZERORPC_ACCESS_LOG": access_log_path
        }

    def tearDown(self):
        os.unlink(self.default_config['ERROR_LOG'])
        os.unlink(self.default_config['ZERORPC_ACCESS_LOG'])

    def test_debug_mode(self):
        clear_handlers()
        app = Zask(__name__)
        app.config = self.default_config
        init_zerorpc(app)

        print ""
        channel_logger.error("error")
        gevent_logger.error("error")
        core_logger.error("error")

    def test_prod_mode(self):
        clear_handlers()
        app = Zask(__name__)
        app.config = self.default_config
        app.config['DEBUG'] = False
        init_zerorpc(app)

        channel_logger.error("error")
        gevent_logger.error("error")
        core_logger.error("error")

        print ""
        print "printing file:"
        with open(app.config['ERROR_LOG'], 'r') as fin:
            print fin.read()

    def test_access_log(self):
        clear_handlers()
        app = Zask(__name__)
        app.config = self.default_config
        init_zerorpc(app)

        @access_log
        class MySrv(object):

            def sleep(self):
                time.sleep(1)

        srv = MySrv()
        print "Should print an access log:"
        srv.sleep()

    def test_default_config(self):
        clear_handlers()
        app = Zask(__name__)
        app.config = {
            "DEBUG": True,
            "ERROR_LOG": ""
        }
        init_zerorpc(app)
        assert app.config['ZERORPC_ACCESS_LOG'] == '/tmp/zerorpc.access.log'


if __name__ == '__main__':
    unittest.main()

"""
    tests.logging
    ~~~~~~~~~~~~~

    This is more like examples than unittest for logging.
"""

import os
import unittest
import tempfile

from zask import Zask
from zask.logging import create_logger


class TestLogging(unittest.TestCase):

    def setUp(self):
        fd, path = tempfile.mkstemp()
        self.default_config = {
            "DEBUG": True,
            "ERROR_LOG": path
        }

    def tearDown(self):
        os.unlink(self.default_config['ERROR_LOG'])

    def test_debug_mode(self):
        app = Zask(__name__)
        app.config = self.default_config
        app.logger.debug("debug")
        app.logger.info("info")
        app.logger.error("error")
        app.logger.exception("exception")

    def test_prod_mode(self):
        app = Zask(__name__)
        app.config = self.default_config
        app.config['DEBUG'] = False
        app.config['PRODUCTION_LOGGING_LEVEL'] = 'warning'
        app.logger.debug("debug")
        app.logger.info("info")
        app.logger.warning("warning")
        app.logger.error("error")
        app.logger.exception("exception")

        print ''
        print 'printing file:'
        with open(app.config['ERROR_LOG'], 'r') as fin:
            print fin.read()

if __name__ == '__main__':
    unittest.main()

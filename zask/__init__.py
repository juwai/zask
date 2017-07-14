# -*- coding: utf-8 -*-

__version__ = '1.9.5'

import gevent
from gevent.local import local

from zask.config import Config
from zask.logging import create_logger
from zask.utils import get_root_path


class Zask(object):

    def __init__(self, import_name):
        self.default_config = {
            'DEBUG': True,
            'ERROR_LOG': '/tmp/zask.error.log'
        }
        self.import_name = import_name
        self.root_path = get_root_path(import_name)
        self.config = Config(self.root_path, self.default_config)
        self._logger = None

    @property
    def logger(self):
        if self._logger:
            return self._logger

        self._logger = logger = create_logger(self.config)
        return logger

    # def __repr__(self):
    #     return '<%s %r>' % (
    #         self.__class__.__name__,
    #         self.name,
    #     )


class LocalContext(object):
    """
    Store data in local greenlet context.

    > Gevent also allows you to specify data which is local to \
      the greenlet context.

    > Internally, this is implemented as a global lookup \
      which addresses a private namespace keyed by the \
      greenlet's getcurrent() value.

    See http://sdiehl.github.io/gevent-tutorial/#thread-locals \
    for information.
    """

    def __init__(self):
        self.stash = local()

    def get_request_cxt(self):
        return gevent.getcurrent()

_request_ctx = LocalContext()

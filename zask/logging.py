# -*- coding: utf-8 -*-
"""
    zask.logging
    ~~~~~~~~~~~~~

    Implements the logging support for Zask.

    :copyright: (c) 2015 by the J5.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import

from logging import getLogger, StreamHandler, Formatter, \
    DEBUG, INFO, WARNING, ERROR
from logging.handlers import RotatingFileHandler

PROD_LOG_FORMAT = (
    '[%(asctime)s] ' +
    '%(name)s %(levelname)s in %(module)s ' +
    '[%(pathname)s:%(lineno)d]: %(message)s'
)
DEBUG_LOG_FORMAT = (
    '-' * 40 + '\n' +
    '%(name)s %(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n' +
    '%(message)s\n'
)


def debug_handler():
    handler = StreamHandler()
    handler.setLevel(DEBUG)
    handler.setFormatter(Formatter(DEBUG_LOG_FORMAT))
    return handler


def production_handler(config):
    handler = RotatingFileHandler(config['ERROR_LOG'],
                                  maxBytes=1024 * 50,
                                  backupCount=5)
    handler.setLevel(_get_production_logging_level(config))
    handler.setFormatter(Formatter(PROD_LOG_FORMAT))
    return handler


def create_logger(config):
    """Creates a logger for the application. Logger's behavior depend on
    ``DEBUG`` flag.Furthermore this function also removes all attached
    handlers in case there was a logger with the log name before.
    """
    logger_ = getLogger(__name__)
    del logger_.handlers[:]

    if config['DEBUG']:
        handler = debug_handler()
        logger_.setLevel(DEBUG)
    else:
        handler = production_handler(config)
        logger_.setLevel(_get_production_logging_level(config))

    logger_.addHandler(handler)
    return logger_


def _get_production_logging_level(config):
    config.setdefault('PRODUCTION_LOGGING_LEVEL', 'INFO')
    mapping = {
        'DEBUG': DEBUG,
        'INFO': INFO,
        'WARNING': WARNING,
        'ERROR': ERROR
    }
    return mapping.get(config['PRODUCTION_LOGGING_LEVEL'].upper()) or INFO

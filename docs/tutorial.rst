.. _tutorial:

########
Tutorial
########

Quickstart
==========

Zask is easy to use::

    from zask import Zask
    from zask.ext.zerorpc import ZeroRPC, access_log

    app = Zask(__name__)
    rpc = ZeroRPC(app, middlewares=None)

    @access_log
    class MySrv(rpc.Server):
        
        def foo(self):
            return "bar"

    server = MySrv()
    server.bind("tcp://0.0.0.0:8081")
    server.run()

Debug Mode
==========

If ``config['DEBUG']`` is ``True``, then all the loggers will sent messages to ``stdout``, otherwise, if ``config['DEUBG']`` is ``False``, messages will be rewrited to the files. For now, there are two loggers in the zask, ``zask logger`` and ``access logger``.

Zask Logger
===========

Basic Usage::

    from zask import Zask

    app = Zask(__name__)

    app.logger.info("info")
    app.logger.debug("debug")
    app.logger.error("error")
    try:
        raise Exception("exception")
    except:
        app.logger.exception("")

Access Logger
=============

Generally speaking, you wont use this logger directly. When you use the ``access_log`` decorator or ``ACCESS_LOG_MIDDLEWARE``, it will working automatically.

.. include:: sqlalchemy.rst

.. include:: zerorpc.rst

Default configures
==================

================================= =========================================
Name                              Description
================================= =========================================
``DEBUG``                         enable/disable debug mode
                                  default: ``True``
``ERROR_LOG``                     the path for the ``zask logger`` 
                                  when ``DEBUG`` is ``False``
                                  default: ``/tmp/zask.error.log``
``ZERORPC_ACCESS_LOG``            the path for the ``access logger`` 
                                  when ``DEBUG`` is ``False``
                                  default: ``/tmp/zask.acess.log``
``SQLALCHEMY_DATABASE_URI``       the main URI for SqlAlchemy
                                  default: ``sqlite://``
``SQLALCHEMY_BINDS``              multiple binds mapping.
                                  default: ``None``
``SQLALCHEMY_NATIVE_UNICODE``     default: ``None``
``SQLALCHEMY_ECHO``               enable/disable echo SqlAlchemy debug
                                  default: ``False``
``SQLALCHEMY_POOL_SIZE``          default: ``None`` 
``SQLALCHEMY_POOL_TIMEOUT``       default: ``None``
``SQLALCHEMY_POOL_RECYCLE``       default: ``3600``    
``SQLALCHEMY_MAX_OVERFLOW``       default: ``None``    
================================= =========================================

Best Practices
==============

Configure loader
----------------

We have several configure files for different envs, dev and prod for example. We can load config files in a special order::

    from zask import Zask

    app = Zask(__name__)

    # which is in the codebase
    app.config.from_pyfile("settings.cfg") 
    
    # which is for development, 
    # ignored by codebase
    app.config.from_pyfile("dev.setting.cfg", silent=True) 

    # which is for production, 
    # deployed by CM tools
    app.config.from_pyfile("/etc/foo.cfg", silent=True) 
    
    # which is work with supervisord
    app.config.from_envvar('CONFIG_PATH', silent=True) 

    # use logger after configure initialize
    app.logger.debug("Config loaded")


Developer
=========

Document
--------

Document is powed by Sphinx.
First, ensure sphinx is installed to the same environment as source code.
Second, run::

    $ sphinx-apidoc
    $ make html

`Note: update your` ``sphinx-build`` `to the real path in` ``Makefile``. 

Testing
-------

Similar to documentation, testing module need to be installed to the same environment.
You can test one file at a time by run the script::

    $ python tests/test_config.py

Or test all the cases with ``tox`` and ``pytest``::

    $ tox

Visit `tox`_ and `pytest`_ for more infomation.

.. _tox: https://tox.readthedocs.org/en/latest/
.. _pytest: http://pytest.org/latest/


API Reference
=============

.. toctree::
   :maxdepth: 4

   zask

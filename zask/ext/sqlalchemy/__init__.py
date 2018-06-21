# -*- coding: utf-8 -*-
"""
    zask.ext.sqlalchemy
    ~~~~~~~~~~~~~~~~~~~
    Adds basic SQLAlchemy support to your application.
    I have not add all the feature, bacause zask is not for web,
    The other reason is i can't handle all the features right now :P

    Differents between Flask-SQLAlchemy:

    1. No default ``scopefunc`` it means that you need define
       how to separate sessions your self
    2. No signal session
    3. No query record
    4. No pagination and HTTP headers, e.g. ``get_or_404``
    5. No difference between app bound and not bound

    :copyright: (c) 2015 by the J5.
    :license: BSD, see LICENSE for more details.

    :copyright: (c) 2012 by Armin Ronacher, Daniel Neuhäuser.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement, absolute_import

import os
import re
import sys
import functools
import sqlalchemy
import atexit
from functools import partial
from sqlalchemy import orm, event
from sqlalchemy.orm.exc import UnmappedClassError
from sqlalchemy.orm.session import Session as SessionBase
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from zask import _request_ctx
from zask.ext.sqlalchemy._compat import iteritems, itervalues, xrange, \
    string_types

_camelcase_re = re.compile(r'([A-Z]+)(?=[a-z0-9])')


def _make_table(db):
    def _make_table(*args, **kwargs):
        if len(args) > 1 and isinstance(args[1], db.Column):
            args = (args[0], db.metadata) + args[1:]
        info = kwargs.pop('info', None) or {}
        info.setdefault('bind_key', None)
        kwargs['info'] = info
        return sqlalchemy.Table(*args, **kwargs)
    return _make_table


def _set_default_query_class(d):
    if 'query_class' not in d:
        d['query_class'] = orm.Query


def _wrap_with_default_query_class(fn):
    @functools.wraps(fn)
    def newfn(*args, **kwargs):
        _set_default_query_class(kwargs)
        if "backref" in kwargs:
            backref = kwargs['backref']
            if isinstance(backref, string_types):
                backref = (backref, {})
            _set_default_query_class(backref[1])
        return fn(*args, **kwargs)
    return newfn


def get_state(app):
    """Gets the state for the application"""
    assert 'sqlalchemy' in app.extensions, \
        'The sqlalchemy extension was not registered to the current ' \
        'application.  Please make sure to call init_app() first.'
    return app.extensions['sqlalchemy']


def _include_sqlalchemy(obj):
    for module in sqlalchemy, sqlalchemy.orm:
        for key in module.__all__:
            if not hasattr(obj, key):
                setattr(obj, key, getattr(module, key))
    # Note: obj.Table does not attempt to be a SQLAlchemy Table class.
    obj.Table = _make_table(obj)
    obj.relationship = _wrap_with_default_query_class(obj.relationship)
    obj.relation = _wrap_with_default_query_class(obj.relation)
    obj.dynamic_loader = _wrap_with_default_query_class(obj.dynamic_loader)
    obj.event = event


def _should_set_tablename(bases, d):
    """Check what values are set by a class and
    its bases to determine if a
    tablename should be automatically generated.

    The class and its bases are checked in order
    of precedence: the class itself then each base
    in the order they were given at class definition.

    Abstract classes do not generate a tablename,
    although they may have set
    or inherited a tablename elsewhere.

    If a class defines a tablename or table,
    a new one will not be generated.
    Otherwise, if the class defines a primary key,
    a new name will be generated.

    This supports:

    * Joined table inheritance without explicitly
      naming sub-models.
    * Single table inheritance.
    * Inheriting from mixins or abstract models.

    :param bases: base classes of new class
    :param d: new class dict
    :return: True if tablename should be set
    """

    if '__tablename__' in d or '__table__' in d or '__abstract__' in d:
        return False

    if any(v.primary_key for v in itervalues(d)
           if isinstance(v, sqlalchemy.Column)):
        return True

    for base in bases:
        if hasattr(base, '__tablename__') or hasattr(base, '__table__'):
            return False

        for name in dir(base):
            attr = getattr(base, name)

            if isinstance(attr, sqlalchemy.Column) and attr.primary_key:
                return True


class _BoundDeclarativeMeta(DeclarativeMeta):

    def __new__(cls, name, bases, d):
        if _should_set_tablename(bases, d):
            def _join(match):
                word = match.group()
                if len(word) > 1:
                    return ('_%s_%s' % (word[:-1], word[-1])).lower()
                return '_' + word.lower()
            d['__tablename__'] = _camelcase_re.sub(_join, name).lstrip('_')

        return DeclarativeMeta.__new__(cls, name, bases, d)

    def __init__(self, name, bases, d):
        bind_key = d.pop('__bind_key__', None)
        DeclarativeMeta.__init__(self, name, bases, d)
        if bind_key is not None:
            self.__table__.info['bind_key'] = bind_key


class BindSession(SessionBase):
    """The BindSession is the default session that Zask-SQLAlchemy
    uses.  It extends the default session system with bind selection.
    If you want to use a different session you can override the
    :meth:`SQLAlchemy.create_session` function.

    """

    def __init__(self, db, autocommit=False, autoflush=True, **options):
        #: The application that this session belongs to.
        self.app = db.get_app()
        bind = options.pop('bind', None) or db.engine
        SessionBase.__init__(self, autocommit=autocommit, autoflush=autoflush,
                             bind=bind,
                             binds=db.get_binds(self.app), **options)

    def get_bind(self, mapper, clause=None):
        # mapper is None if someone tries to just get a connection
        if mapper is not None:
            info = getattr(mapper.mapped_table, 'info', {})
            bind_key = info.get('bind_key')
            if bind_key is not None:
                state = get_state(self.app)
                return state.db.get_engine(self.app, bind=bind_key)
        return SessionBase.get_bind(self, mapper, clause)


class _SQLAlchemyState(object):
    """Remembers configuration for the (db, app) tuple."""

    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.connectors = {}


class _QueryProperty(object):

    def __init__(self, sa):
        self.sa = sa

    def __get__(self, obj, type):
        try:
            mapper = orm.class_mapper(type)
            if mapper:
                return type.query_class(mapper, session=self.sa.session())
        except UnmappedClassError:
            return None


class _EngineConnector(object):

    def __init__(self, sa, app, bind=None):
        self._sa = sa
        self._app = app
        self._engine = None
        self._connected_for = None
        self._bind = bind

    def get_uri(self):
        if self._bind is None:
            return self._app.config['SQLALCHEMY_DATABASE_URI']
        binds = self._app.config.get('SQLALCHEMY_BINDS') or ()
        assert self._bind in binds, \
            'Bind %r is not specified.  Set it in the SQLALCHEMY_BINDS ' \
            'configuration variable' % self._bind
        return binds[self._bind]

    def get_engine(self):
        uri = self.get_uri()
        echo = self._app.config['SQLALCHEMY_ECHO']
        if (uri, echo) == self._connected_for:
            return self._engine
        info = make_url(uri)
        # options = {'convert_unicode': True}
        options = {}
        self._sa.apply_pool_defaults(self._app, options)
        self._sa.apply_driver_hacks(self._app, info, options)
        if echo:
            options['echo'] = True
        self._engine = rv = sqlalchemy.create_engine(info, **options)
        self._connected_for = (uri, echo)
        return rv


class Model(object):
    """Baseclass for custom user models."""

    #: the query class used.  The :attr:`query` attribute is an instance
    #: of this class.  By default a ``orm.Query`` is used.
    query_class = orm.Query

    #: an instance of :attr:`query_class`.  Can be used to query the
    #: database for instances of this model.
    query = None


class SQLAlchemy(object):
    """This class is used to control the SQLAlchemy integration to one
    or more Zask applications.

    There are two usage modes which work very similarly.  One is binding
    the instance to a very specific Zask application::

        app = Zask(__name__)
        db = SQLAlchemy(app)

    The second possibility is to create the object once and configure the
    application later to support it::

        db = SQLAlchemy()
        def create_app():
            app = Zask(__name__)
            db.init_app(app)
            return app

    This class also provides access to all the SQLAlchemy functions and classes
    from the :mod:`sqlalchemy` and :mod:`sqlalchemy.orm` modules.  So you can
    declare models like this::

        class User(db.Model):
            username = db.Column(db.String(80), unique=True)
            pw_hash = db.Column(db.String(80))

    """

    def __init__(self, app=None,
                 use_native_unicode=True,
                 session_options=None):
        self.use_native_unicode = use_native_unicode

        if session_options is None:
            session_options = {}

        if app is not None:
            self.init_app(app)
        else:
            self.app = None

        session_options.setdefault('scopefunc', _request_ctx.get_request_cxt)
        self.session = self.create_scoped_session(session_options)
        self.Query = orm.Query
        self.Model = self.make_declarative_base()

        _include_sqlalchemy(self)

        @atexit.register
        def shutdown_session():
            self.session.remove()

    @property
    def metadata(self):
        """Returns the metadata"""
        return self.Model.metadata

    def create_scoped_session(self, options=None):
        """Helper factory method that creates a scoped session.  It
        internally calls :meth:`create_session`.
        """
        if options is None:
            options = {}
        scopefunc = options.pop('scopefunc', None)
        return orm.scoped_session(partial(self.create_session, options),
                                  scopefunc=scopefunc)

    def create_session(self, options):
        """Creates the session.  The default implementation returns a
        :class:`BindSession`.
        """
        return BindSession(self, **options)

    def make_declarative_base(self):
        """Creates the declarative base."""
        base = declarative_base(cls=Model, name='Model',
                                metaclass=_BoundDeclarativeMeta)
        base.query = _QueryProperty(self)
        return base

    def init_app(self, app):
        """This callback can be used to initialize an application for the
        use with this database setup.  Never use a database in the context
        of an application not initialized that way or connections will
        leak.
        """
        self.app = app
        app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite://')
        app.config.setdefault('SQLALCHEMY_BINDS', None)
        app.config.setdefault('SQLALCHEMY_NATIVE_UNICODE', None)
        app.config.setdefault('SQLALCHEMY_ECHO', False)
        app.config.setdefault('SQLALCHEMY_POOL_SIZE', None)
        app.config.setdefault('SQLALCHEMY_POOL_TIMEOUT', None)
        # as we gonna run zask as a daemon, set pool_recycle as default
        app.config.setdefault('SQLALCHEMY_POOL_RECYCLE', 3600)
        app.config.setdefault('SQLALCHEMY_MAX_OVERFLOW', None)
        if sqlalchemy.__version__.startswith('1.2'):
            app.config.setdefault('POOL_PRE_PING', False)

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['sqlalchemy'] = _SQLAlchemyState(self, app)

    def apply_pool_defaults(self, app, options):
        def _setdefault(optionkey, configkey):
            value = app.config[configkey]
            if value is not None:
                options[optionkey] = value
        _setdefault('pool_size', 'SQLALCHEMY_POOL_SIZE')
        _setdefault('pool_timeout', 'SQLALCHEMY_POOL_TIMEOUT')
        _setdefault('pool_recycle', 'SQLALCHEMY_POOL_RECYCLE')
        _setdefault('max_overflow', 'SQLALCHEMY_MAX_OVERFLOW')
        if sqlalchemy.__version__.startswith('1.2'):
            _setdefault('pool_pre_ping', 'POOL_PRE_PING')

    def apply_driver_hacks(self, app, info, options):
        """This method is called before engine creation and used to inject
        driver specific hacks into the options.  The `options` parameter is
        a dictionary of keyword arguments that will then be used to call
        the :func:`sqlalchemy.create_engine` function.

        The default implementation provides some saner defaults for things
        like pool sizes for MySQL and sqlite.  Also it injects the setting of
        `SQLALCHEMY_NATIVE_UNICODE`.
        """
        if info.drivername.startswith('mysql'):
            info.query.setdefault('charset', 'utf8')
            if info.drivername != 'mysql+gaerdbms':
                options.setdefault('pool_size', 10)
                options.setdefault('pool_recycle', 7200)
        elif info.drivername == 'sqlite':
            pool_size = options.get('pool_size')
            detected_in_memory = False
            # we go to memory and the pool size was explicitly set to 0
            # which is fail.  Let the user know that
            if info.database in (None, '', ':memory:'):
                detected_in_memory = True
                if pool_size == 0:
                    raise RuntimeError('SQLite in memory database with an '
                                       'empty queue not possible due to data '
                                       'loss.')
            # if pool size is None or explicitly set to 0 we assume the
            # user did not want a queue for this sqlite connection and
            # hook in the null pool.
            elif not pool_size:
                from sqlalchemy.pool import NullPool
                options['poolclass'] = NullPool

            # if it's not an in memory database we make the path absolute.
            if not detected_in_memory:
                info.database = os.path.join(app.root_path, info.database)

        unu = app.config['SQLALCHEMY_NATIVE_UNICODE']
        if unu is None:
            unu = self.use_native_unicode
        if not unu:
            options['use_native_unicode'] = False

    @property
    def engine(self):
        """Gives access to the engine.
        If the database configuration is bound
        to a specific application (initialized
        with an application) this will
        always return a database connection.
        If however the current application
        is used this might raise a :exc:`RuntimeError`
        if no application is
        active at the moment.
        """
        return self.get_engine(self.get_app())

    def make_connector(self, app, bind=None):
        """Creates the connector for a given state and bind."""
        return _EngineConnector(self, app, bind)

    def get_engine(self, app, bind=None):
        """Returns a specific engine.
        """
        state = get_state(app)
        connector = state.connectors.get(bind)
        if connector is None:
            connector = self.make_connector(app, bind)
            state.connectors[bind] = connector
        return connector.get_engine()

    def get_app(self, reference_app=None):
        """Helper method that implements the logic to look up an application.
        """
        if reference_app is not None:
            return reference_app
        if self.app is not None:
            return self.app
        raise RuntimeError('application not registered on db '
                           'instance and no application bound '
                           'to current context')

    def get_tables_for_bind(self, bind=None):
        """Returns a list of all tables relevant for a bind."""
        result = []
        for table in itervalues(self.Model.metadata.tables):
            if table.info.get('bind_key') == bind:
                result.append(table)
        return result

    def get_binds(self, app=None):
        """Returns a dictionary with a table->engine mapping.

        This is suitable for use of sessionmaker(binds=db.get_binds(app)).
        """
        app = self.get_app(app)
        binds = [None] + list(app.config.get('SQLALCHEMY_BINDS') or ())
        retval = {}
        for bind in binds:
            engine = self.get_engine(app, bind)
            tables = self.get_tables_for_bind(bind)
            retval.update(dict((table, engine) for table in tables))
        return retval

    def _execute_for_all_tables(self, app, bind, operation):
        app = self.get_app(app)

        if bind == '__all__':
            binds = [None] + list(app.config.get('SQLALCHEMY_BINDS') or ())
        elif isinstance(bind, basestring) or bind is None:
            binds = [bind]
        else:
            binds = bind

        for bind in binds:
            tables = self.get_tables_for_bind(bind)
            op = getattr(self.Model.metadata, operation)
            op(bind=self.get_engine(app, bind), tables=tables)

    def create_all(self, bind='__all__', app=None):
        """Creates all tables.
        """
        self._execute_for_all_tables(app, bind, 'create_all')

    def drop_all(self, bind='__all__', app=None):
        """Drops all tables.
        """
        self._execute_for_all_tables(app, bind, 'drop_all')

    def reflect(self, bind='__all__', app=None):
        """Reflects tables from the database.

        """
        self._execute_for_all_tables(app, bind, 'reflect')

    def __repr__(self):
        app = None
        if self.app is not None:
            app = self.app
        return '<%s engine=%r>' % (
            self.__class__.__name__,
            app and app.config['SQLALCHEMY_DATABASE_URI'] or None
        )


class SessionMiddleware(object):

    def __init__(self, db):
        self.db = db

    def server_after_exec(self, request_event, reply_event):
        self.db.session.remove()

    def server_inspect_exception(
            self,
            request_event,
            reply_event,
            task_context,
            exc_infos):
        self.db.session.remove()

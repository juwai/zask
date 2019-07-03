# -*- coding: utf-8 -*-
"""
    zask.ext.zerorpc
    ~~~~~~~~~~~~~~~~

    Add zerorpc support to zask.

    :copyright: (c) 2015 by the J5.
    :license: BSD, see LICENSE for more details.
"""
import inspect
import gevent
import time
import uuid

import zerorpc
from zerorpc.heartbeat import HeartBeatOnChannel
from zerorpc.channel import BufferedChannel, logger as channel_logger
from zerorpc.gevent_zmq import logger as gevent_logger
from zerorpc.core import logger as core_logger

from logging import DEBUG, ERROR, Formatter, getLogger, INFO, StreamHandler
from logging.handlers import TimedRotatingFileHandler
from zask import _request_ctx
from zask.logging import debug_handler, production_handler

# Because the time module has a problem with timezones, we now format all log
# message dates in UTC. We tried replacing the Formatter using tzlocal but it
# was very slow calling it the first time. The delay is somewhere in the range
# of 3-4 seconds. This is not acceptable in a production application. So until
# we find a better solution, this is the compromise.
Formatter.converter = time.gmtime

access_logger = getLogger(__name__)

# NCSA Combined Log Format + request time + uuid
ACCESS_LOG_FORMAT = (
    '%(host)s %(identifier)s %(username)s %(asctime)s %(message)s ' +
    '%(status_code)s %(bytes)s %(referrer)s %(user_agent)s %(cookies)s ' +
    '%(request_time)d %(uuid)s'
)
ACCESS_LOG_DATETIME_FORMAT = '[%d/%b/%Y:%H:%M:%S +0000]'  # Hard coded for UTC

CONFIG_ENDPOINT_MIDDLEWARE = 'file'
CONFIG_CUSTOME_HEADER_MIDDLEWARE = 'header'
ACCESS_LOG_MIDDLEWARE = 'access_log'
REQUEST_CHAIN_MIDDLEWARE = 'uuid'
REQUEST_EVENT_MIDDLEWARE = 'event'
DEFAULT_MIDDLEWARES = [
    CONFIG_CUSTOME_HEADER_MIDDLEWARE,
    REQUEST_CHAIN_MIDDLEWARE,
    ACCESS_LOG_MIDDLEWARE,
    REQUEST_EVENT_MIDDLEWARE
]


def _milli_time():
    """get millionsecond of time.
    """
    return int(round(time.time() * 1000))


def _log(cls_name, func):
    """[Deprecated]
    Decorator for every method of server to record simple access log.
    """

    def wrapped(*args, **kwargs):
        start = _milli_time()
        result = func(*args, **kwargs)
        log = '"%s" - "%s" - OK - %dms' % (cls_name,
                                           func.__name__,
                                           _milli_time() - start)
        access_logger.info(log, extra={'access_key': None})
        return result
    return wrapped


def access_log(cls):
    """[Deprecated]
    A decorator for zerorpc server class to generate access logs::

        @access_log
        Class MySrv(Object):

            def foo(self)
                return "bar"

    Every request from client will create a log::

        [2014-12-18 13:33:16,433] - None - "MySrv" - "foo" - OK - 1ms

    :param cls: the class object
    """
    for name, m in inspect.getmembers(cls, inspect.ismethod):
        setattr(cls, name, _log(cls.__name__, m))
    return cls


def init_zerorpc(app):
    """Baskward compatibility.
    """
    return ZeroRPC(app)


class ConfigMiddleware(object):

    """A middleware work with configure of zask application.

    This is the base class for all the config based middlewares.
    """

    def __init__(self, app):
        self.app = app

    def _get_config_name(self, name):
        config_name = "ZERORPC_%s" % (name.upper())
        if self.app.config.get(config_name) is None:
            raise MissingConfigException(config_name)
        return config_name

    def get_version(self, name, version):
        config_name = self._get_config_name(name)
        if version is None:
            try:
                version = self.app.config[config_name]['default']
            except:
                raise ClientMissingVersionException()
            else:
                version = self.app.config[config_name]['default']
        if self.app.config.get(config_name).get(version) is None:
            raise MissingConfigException(config_name + '["' + version + '"]')
        return version

    def get_endpoint(self, name, version):
        config_name = self._get_config_name(name)
        version = self.get_version(name, version)
        return self.app.config[config_name][version]

    def get_access_key(self, name):
        config_name = self._get_config_name(name)
        if self.app.config.get(config_name).get('access_key') is None:
            raise MissingAccessKeyException(config_name)
        return self.app.config[config_name]['access_key']

    def get_client_keys(self, name):
        config_name = self._get_config_name(name)
        return self.app.config.get(config_name).get('client_keys', None)


class ConfigEndpointMiddleware(ConfigMiddleware):

    """Resolve the endpoint by service name.
    """

    def resolve_endpoint(self, endpoint):
        # when configured multiple endpoint,
        # i don't want sub endpoint also be decoded.
        # so ignore that and return directly.
        try:
            name, version = HandleEndpoint.decode(endpoint)
        except ValueError:
            return endpoint
        else:
            return self.get_endpoint(name, version)


class ConfigCustomHeaderMiddleware(ConfigEndpointMiddleware):

    """Besides resolve the endpoint by service name,
    add custome header to the client.

    Server side will do the validation for the access key and service version.
    """
    _server_version = None

    def set_server_version(self, version):
        self._server_version = version

    def client_before_request(self, event):
        if event.header.get('service_name'):
            event.header.update(
                {
                    'access_key': self.get_access_key(
                        event.header['service_name']),
                    'service_version': self.get_version(
                        event.header['service_name'],
                        event.header['service_version'])})

    def load_task_context(self, event_header):
        if event_header.get('service_version') and event_header.get(
                'service_version') != self._server_version:
            raise VersionNotMatchException(event_header.get('access_key'),
                                           event_header.get('service_version'),
                                           self._server_version)
        if event_header.get('access_key'):
            keys = self.get_client_keys(event_header['service_name'])
            if keys and event_header.get('access_key') not in keys:
                raise NoSuchAccessKeyException(event_header.get('access_key'))


class RequestChainMiddleware(object):
    """Generate UUID for requests and store in greenlet's local storage
    """

    def __init__(self, app):
        self.app = app

    def get_uuid(self):
        if not hasattr(_request_ctx.stash, 'uuid'):
            setattr(_request_ctx.stash, 'uuid', str(uuid.uuid1()))
        return _request_ctx.stash.uuid

    def get_origin_access_key(self):
        if not hasattr(_request_ctx.stash, 'origin_access_key'):
            return None
        return _request_ctx.stash.origin_access_key

    def set_uuid(self, uuid):
        setattr(_request_ctx.stash, 'uuid', uuid)

    def clear_uuid(self):
        if hasattr(_request_ctx.stash, 'uuid'):
            delattr(_request_ctx.stash, 'uuid')

    def server_before_exec(self, request_event):
        if not request_event.header.get('uuid'):
            request_event.header.update({
                'uuid': self.get_uuid(),
            })
        else:
            self.set_uuid(request_event.header.get('uuid'))
        if request_event.header.get('origin_access_key'):
            self.set_origin_access_key(
                request_event.header.get('origin_access_key'))
        elif request_event.header.get('access_key'):
            self.set_origin_access_key(request_event.header.get('access_key'))

    def set_origin_access_key(self, origin_access_key):
        setattr(_request_ctx.stash, 'origin_access_key', origin_access_key)

    def clear_origin_access_key(self):
        if hasattr(_request_ctx.stash, 'origin_access_key'):
            delattr(_request_ctx.stash, 'origin_access_key')

    def server_after_exec(self, request_event, reply_event):
        self.clear_uuid()
        self.clear_origin_access_key()

    def server_inspect_exception(
            self,
            request_event,
            reply_event,
            task_context,
            exc_infos):
        self.clear_uuid()

    def client_before_request(self, event):
        if not event.header.get('uuid'):
            event.header.update({
                'uuid': self.get_uuid(),
            })
        if not event.header.get('origin_access_key'):
            if self.get_origin_access_key():
                event.header.update({
                    'origin_access_key': self.get_origin_access_key()
                })


class RequestEventMiddleware(object):
    """Exposes the request_event to the object being passed to Server()
    via self.get_request_event() from a service endpoint.
    """

    def server_before_exec(self, request_event):
        """Injects the request_event into greenlet's local storage context.
        """
        setattr(_request_ctx.stash, 'request_event', request_event)


class AccessLogMiddleware(object):

    """This can't be used before initialize the logger.
    """
    _class_name = None

    def __init__(self, app):
        self.app = app

    def set_class_name(self, class_name):
        self._class_name = class_name

    def server_before_exec(self, request_event):
        request_event.header.update({
            'started_at': _milli_time()
        })

    def server_after_exec(self, request_event, reply_event):
        start = request_event.header.get('started_at')
        message = '"%s %s"' % (self._class_name, request_event.name)
        access_key = request_event.header.get('access_key', '-')
        uuid = request_event.header.get('uuid', '-')
        access_logger.info(message, extra={
            'host': '-',
            'identifier': '-',
            'username': access_key,
            'status_code': 'OK',
            'bytes': '-',
            'referrer': '-',
            'user_agent': '-',
            'cookies': '-',
            'request_time': _milli_time() - start,
            'uuid': uuid,
        })

    def server_inspect_exception(
            self,
            request_event,
            reply_event,
            task_context,
            exc_infos):
        start = request_event.header.get('started_at')
        message = '"%s %s"' % (self._class_name, request_event.name)
        access_key = request_event.header.get('access_key', '-')
        uuid = request_event.header.get('uuid', '-')
        access_logger.info(message, extra={
            'host': '-',
            'identifier': '-',
            'username': access_key,
            'status_code': 'ERROR',
            'bytes': '-',
            'referrer': '-',
            'user_agent': '-',
            'cookies': '-',
            'request_time': _milli_time() - start if start else 0,
            'uuid': uuid,
        })


class ZeroRPC(object):

    """This is a class used to integrate zerorpc to the Zask application.

    ZeroRPC extention provides a few powful middlewares.

    Take ``CONFIG_ENDPOINT_MIDDLEWARE`` as example,
    which will resolve endpoint according to the
    zask application configuration. To use that you can setup a
    ZeroRPC like this::

        app = Zask(__name__)
        app.config['ZERORPC_SOME_SERVICE'] = {
            '1.0': endpoint,
        }
        rpc = ZeroRPC(app, middlewares=[CONFIG_ENDPOINT_MIDDLEWARE])

    Then create a server and a client::

        class Srv(object):
            __version__ = "1.0"
            __service_name__ = "some_service"

        def hello(self):
            return 'world'

        client = rpc.Client('some_service', version='1.0')
        client.hello()

    Application will look for ``RPC_SOME_SERVICE`` config. You can set a
    default version to make the client initialization more easier::

        app.config['ZERORPC_SOME_SERVICE'] = {
            '1.0': endpoint,
            '2.0': [ # set list if you have multiple endpoints
                endpoint1,
                endpoint2
            ]
            'default': '1.0'
        }
        client = rpc.Client('some_service')
        client.hello()

    But if you don't want to use the middlewares, just set ``middlewares``
    to ``None``::

        app = Zask(__name__)
        rpc = ZeroRPC(app, middlewares=None)

    Or set a new context to the Server/Client during the runtime::

        app = Zask(__name__)
        rpc = ZeroRPC(app, middlewares=[CONFIG_ENDPOINT_MIDDLEWARE])

        default_context = zerorpc.Context().get_instance()
        srv = rpc.Server(Srv(), context=default_context)
        client = rpc.Client(context=default_context)

    """

    def __init__(self, app=None, middlewares=DEFAULT_MIDDLEWARES):
        self._middlewares = middlewares
        self.Server = _Server
        self.Client = _Client
        if app is not None:
            self.init_app(app)
        else:
            self.app = None

    def init_app(self, app):
        """Initial the access logger and zerorpc exception handlers.

        :param app: current zask application
        """
        self.app = app
        app.config.setdefault('ZERORPC_ACCESS_LOG', '/tmp/zerorpc.access.log')
        self._init_zerorpc_logger()
        if self._middlewares:
            self._init_zerorpc_context()
        else:
            _Server.__context__ = _Client.__context__ = None

    def _init_zerorpc_context(self):
        context = zerorpc.Context()
        # there is a conflict when binding the endpoint
        # so don't register both middleware
        if CONFIG_CUSTOME_HEADER_MIDDLEWARE in self._middlewares:
            context.register_middleware(ConfigCustomHeaderMiddleware(self.app))

        elif CONFIG_ENDPOINT_MIDDLEWARE in self._middlewares:
            context.register_middleware(ConfigEndpointMiddleware(self.app))

        if REQUEST_CHAIN_MIDDLEWARE in self._middlewares:
            context.register_middleware(RequestChainMiddleware(self.app))

        if ACCESS_LOG_MIDDLEWARE in self._middlewares:
            context.register_middleware(AccessLogMiddleware(self.app))

        if REQUEST_EVENT_MIDDLEWARE in self._middlewares:
            context.register_middleware(RequestEventMiddleware())

        _Server.__context__ = _Client.__context__ = context

    def register_middleware(self, middleware):
        context = _Server.__context__ or zerorpc.Context()
        context.register_middleware(middleware)
        _Server.__context__ = _Client.__context__ = context

    def _init_zerorpc_logger(self):
        if self.app.config['DEBUG']:
            access_handler = StreamHandler()
            error_handler = debug_handler()
        else:
            access_handler = TimedRotatingFileHandler(
                self.app.config['ZERORPC_ACCESS_LOG'],
                when='D',
                interval=1,
                backupCount=15)
            error_handler = production_handler(self.app.config)

        access_handler.setLevel(INFO)
        access_handler.setFormatter(Formatter(ACCESS_LOG_FORMAT,
                                              ACCESS_LOG_DATETIME_FORMAT))
        access_logger.setLevel(INFO)
        del access_logger.handlers[:]
        access_logger.addHandler(access_handler)

        channel_logger.addHandler(error_handler)
        gevent_logger.addHandler(error_handler)
        core_logger.addHandler(error_handler)


class _Server(zerorpc.Server):

    """Extends zerorpc.Server by the middlewares
    """
    __version__ = None
    __service_name__ = None
    __context__ = None

    def __init__(self, methods=None, context=None, **kargs):
        if methods is None:
            methods = self

        context_ = context \
            or _Server.__context__ \
            or zerorpc.Context.get_instance()
        heartbeat = kargs.pop('heartbeat', None)
        zerorpc.Server.__init__(self,
                                methods,
                                context=context_,
                                heartbeat=heartbeat,
                                **kargs)

        # Inject get_request_event *after* Server constructor so that
        # it's not exposed to the RPC from the outside.
        methods.get_request_event = self._get_request_event

        for instance in context_._middlewares:
            if isinstance(instance, ConfigEndpointMiddleware):
                if methods.__version__ is None:
                    raise NoVersionException()
                if methods.__service_name__ is None:
                    raise NoNameException()
                self.bind(HandleEndpoint.encode(methods.__service_name__,
                                                methods.__version__))
            if isinstance(instance, ConfigCustomHeaderMiddleware):
                instance.set_server_version(methods.__version__)
            if isinstance(instance, AccessLogMiddleware):
                instance.set_class_name(methods.__class__.__name__)

    def _get_request_event(self):
        """Returns the request_event from the local greenlet storage.
        Requires RequestEventMiddleware to be enabled to work.
        """
        enabled_middlewares = [mw.__class__.__name__ for mw in
                               self.__context__._middlewares]
        if 'RequestEventMiddleware' not in enabled_middlewares:
            raise MissingMiddlewareException('RequestEventMiddleware')
        return getattr(_request_ctx.stash, 'request_event')


class _Client(zerorpc.Client):

    """Extends zerorpc.Client by the middlewares
    """
    __context__ = None

    def __init__(self, connect_to=None, context=None, version=None, **kargs):
        self._connect_to = connect_to
        self._service_version = version
        heartbeat = kargs.pop('heartbeat', None)
        context_ = context \
            or _Client.__context__ \
            or zerorpc.Context.get_instance()
        # let this client handle connect all the time by setting
        # connect_to=None
        zerorpc.Client.__init__(
            self,
            connect_to=None,
            context=context_,
            heartbeat=heartbeat,
            **kargs)
        if connect_to:
            connected = False
            # this is tricky
            # because the hook_resolve_endpoint only accept endpoint
            # so i made a encode and decode for the server_name and version
            for instance in context_._middlewares:
                if isinstance(instance, ConfigMiddleware):
                    self.connect(HandleEndpoint.encode(connect_to, version))
                    connected = True
                    break
            if not connected:
                self.connect(connect_to)

    def _generate_request_event(self, channel, method, args):
        xheader = self._context.hook_get_task_context()
        if self._context._hooks['client_before_request']:
            xheader.update({
                'service_name': self._connect_to,
                'service_version': self._service_version
            })
        request_event = channel.new_event(method, args, xheader)
        self._context.hook_client_before_request(request_event)
        return request_event

    def __call__(self, method, *args, **kargs):
        timeout = kargs.get('timeout', self._timeout)
        channel = self._multiplexer.channel()
        hbchan = HeartBeatOnChannel(channel, freq=self._heartbeat_freq,
                                    passive=self._passive_heartbeat)
        bufchan = BufferedChannel(hbchan, inqueue_size=kargs.get('slots', 100))

        request_event = self._generate_request_event(bufchan, method, args)
        bufchan.emit_event(request_event)

        try:
            if kargs.get('async', False) is False:
                return self._process_response(request_event, bufchan, timeout)

            async_result = gevent.event.AsyncResult()
            gevent.spawn(self._process_response, request_event, bufchan,
                         timeout).link(async_result)
            return async_result
        except:
            # XXX: This is going to be closed twice if async is false and
            # _process_response raises an exception. I wonder if the above
            # async branch can raise an exception too, if no we can just remove
            # this code.
            bufchan.close()
            raise


class HandleEndpoint(object):

    @staticmethod
    def encode(name, version):
        # TODO: validate the name. only [A-Za-z] and _ are acceptable
        return [name, version]

    @staticmethod
    def decode(endpoint):
        [name, version] = endpoint
        return name, version


class NoSuchAccessKeyException(Exception):

    def __init__(self, access_key):
        self.access_key = access_key

    def __str__(self):
        return "No such key '%s'." % self.access_key


class VersionNotMatchException(Exception):

    def __init__(self, access_key, request_version, server_version):
        self.access_key = access_key
        self.request_version = request_version
        self.server_version = server_version

    def __str__(self):
        return "The request version %s from client %s is not match %s." % \
            (self.request_version, self.access_key, self.server_version)


class MissingAccessKeyException(Exception):

    def __init__(self, config_name):
        self.config_name = config_name

    def __str__(self):
        return "Missing 'access_key' in the '%s'." % self.config_name


class MissingConfigException(Exception):

    def __init__(self, config_name):
        self.config_name = config_name

    def __str__(self):
        return "Missing config '%s' in your application." % self.config_name


class ClientMissingVersionException(Exception):

    def __str__(self):
        return "Client missing version. " \
            "You can set a default one or specify one when request."


class NoVersionException(Exception):

    def __str__(self):
        return "__version__ is needed for ZeroRPC server"


class NoNameException(Exception):

    def __str__(self):
        return "__service_name__ is needed for ZeroRPC server"


class MissingMiddlewareException(Exception):
    """Raised when Zask tries to invoke a functionality provided
    by a specific middleware, but that middleware is not loaded.
    """

    def __init__(self, middleware):
        self.middleware = middleware

    def __str__(self):
        return 'Missing required middleware {}.'.format(self.middleware)

# -*- coding: utf-8 -*-
import pytest
import gevent
import zerorpc

from zask import Zask
from zask.ext.zerorpc import *
from testutils import random_ipc_endpoint


def test_no_middleware_runtime():
    app = Zask(__name__)
    endpoint = random_ipc_endpoint()
    rpc = ZeroRPC(app)

    class Srv(rpc.Server):
        __version__ = "1.0"
        __service_name__ = "some_service"

        def hello(self):
            return 'world'

    default_context = zerorpc.Context().get_instance()
    srv = Srv(context=default_context)
    assert srv._context._middlewares == []
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = rpc.Client(endpoint, context=default_context)
    assert client.hello() == 'world'


def test_no_middleware_context():
    app = Zask(__name__)
    endpoint = random_ipc_endpoint()
    rpc = ZeroRPC(app, middlewares=None)

    class Srv(rpc.Server):
        __version__ = "1.0"
        __service_name__ = "some_service"

        def hello(self):
            return 'world'

    srv = Srv()
    assert srv._context._middlewares == []
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = rpc.Client(endpoint)
    assert client.hello() == 'world'


def test_config_endpoint_1():
    app = Zask(__name__)
    endpoint = random_ipc_endpoint()
    app.config['ZERORPC_SOME_SERVICE'] = {
        '1.0': endpoint,
    }
    rpc = ZeroRPC(app, middlewares=[CONFIG_ENDPOINT_MIDDLEWARE])

    class Srv(rpc.Server):
        __version__ = "1.0"
        __service_name__ = "some_service"

        def hello(self):
            return 'world'

    srv = Srv()
    gevent.spawn(srv.run)

    client = rpc.Client('some_service', version='1.0')
    assert client.hello() == 'world'

    with pytest.raises(ClientMissingVersionException):
        client = rpc.Client('some_service')

    client.close()
    srv.close()


def test_config_multiple_endpoints():
    app = Zask(__name__)
    endpoint = random_ipc_endpoint()
    another_endpoint = random_ipc_endpoint()

    app.config['ZERORPC_SOME_SERVICE'] = {
        '1.0': endpoint,
    }
    app.config['ZERORPC_SOME_SERVICE_2'] = {
        '1.0': another_endpoint
    }
    app.config['ZERORPC_SOME_SERVICE_CLIENT'] = {
        '1.0': [
            endpoint,
            another_endpoint
        ],
        'default': '1.0'
    }
    rpc = ZeroRPC(app, middlewares=[CONFIG_ENDPOINT_MIDDLEWARE])

    class Srv(object):
        __version__ = "1.0"
        __service_name__ = "some_service"

        def hello(self):
            return 'i am server 1'

    class AnotherSrv(object):
        __version__ = "1.0"
        __service_name__ = "some_service_2"

        def hello(self):
            return 'i am server 2'

    srv = rpc.Server(Srv())
    another_srv = rpc.Server(AnotherSrv())
    gevent.spawn(srv.run)
    gevent.spawn(another_srv.run)

    client = rpc.Client('some_service_client')
    for i in range(5):
        who_i_am = client.hello()
        app.logger.debug(who_i_am)
        assert who_i_am == 'i am server 1' or who_i_am == 'i am server 2'

    with pytest.raises(MissingConfigException):
        client = rpc.Client('some_service_client', version='2.0')

    client.close()
    srv.close()
    another_srv.close()


def test_custom_header():

    @access_log
    class Srv(object):
        __version__ = "2.0"
        __service_name__ = "some_service"

        def hello(self):
            return 'world'

    app = Zask(__name__)
    endpoint = random_ipc_endpoint()
    app.config['DEBUG'] = False  # for testing accesslog
    app.config['ZERORPC_SOME_SERVICE'] = {
        '2.0': endpoint,
        '1.0': endpoint,
        'client_keys': ['key'],
        'access_key': 'key',
        'default': '2.0'
    }
    rpc = ZeroRPC(app, middlewares=[
        CONFIG_CUSTOME_HEADER_MIDDLEWARE,
        ACCESS_LOG_MIDDLEWARE
    ])

    srv = rpc.Server(Srv())
    gevent.spawn(srv.run)

    client = rpc.Client('some_service')
    channel = client._multiplexer.channel()
    hbchan = HeartBeatOnChannel(channel, freq=client._heartbeat_freq,
                                passive=client._passive_heartbeat)
    bufchan = BufferedChannel(hbchan, inqueue_size=100)
    request_event = client._generate_request_event(bufchan, 'hello', None)
    assert request_event.header['access_key'] == 'key'
    assert request_event.header['service_version'] == '2.0'
    assert client.hello() == 'world'

    app.config['ZERORPC_SOME_SERVICE']['default'] = '1.0'
    with pytest.raises(zerorpc.RemoteError) as excinfo:
        client.hello()
    assert 'VersionNotMatchException' in str(excinfo.value)

    app.config['ZERORPC_SOME_SERVICE']['default'] = '2.0'
    app.config['ZERORPC_SOME_SERVICE']['access_key'] = 'key_error'
    with pytest.raises(zerorpc.RemoteError) as excinfo:
        client.hello()
    assert 'NoSuchAccessKeyException' in str(excinfo.value)

    app.config['ZERORPC_SOME_SERVICE']['client_keys'] = None
    client = rpc.Client('some_service')
    assert client.hello() == 'world'

    client.close()
    srv.close()

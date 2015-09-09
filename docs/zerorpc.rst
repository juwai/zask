Zask-ZeroRPC
============

Middleware in zerorpc is designed to provide a flexible way to change the RPC behavior. Zask-ZeroRPC provides a few features by the built-in middlewares.

Configuration Based Middleware
------------------------------

Endpoint middleware
^^^^^^^^^^^^^^^^^^^

First is the ``CONFIG_ENDPOINT_MIDDLEWARE``, which will resolve endpoint 
according to the zask application configuration. To use that you can setup a 
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
    server = rpc.Server(Srv())
    # don't need bind anymore
    # rpc.Server will do that for you
    server.run()
    client = rpc.Client('some_service', version='1.0')
    client.hello()

Application will look for ``RPC_SOME_SERVICE`` config, which is combined the ``RPC_`` prefix and upper case of ``some_service``. You can set a default version to make the client initialization more easier::

    app.config['ZERORPC_SOME_SERVICE'] = {
        '1.0': endpoint,
        'default': '1.0'
    }
    client = rpc.Client('some_service')
    client.hello()

Custom Header Middleware
^^^^^^^^^^^^^^^^^^^^^^^^

This is a default middleware.

We want to figure out where the request come from and deploy multiple version for one service. So we have to send the ``version`` and the ``access_key`` in the header, and validate the two in the server side::

    app = Zask(__name__)
    app.config['ZERORPC_SOME_SERVICE'] = {
        '2.0': new_endpoint,
        '1.0': old_endpoint,
        'client_keys': ['foo_client_key', 'bar_client_key'],
        'access_key': 'foo_client_key',
        'default': '2.0'
    }

    # as this is the default middleware
    # second parameter can be omitted
    rpc = ZeroRPC(app) 
    srv = rpc.Server(Srv())
    srv.run()
    client = rpc.Client('some_service')

Request header would be like this::

    {
        'message_id': message_id,
        'v': 3,
        'service_name': 'some_service',
        'service_version': '2.0',
        'access_key': 'foo_client_key'
    }

If ``access_key`` is not within the ``client_keys`` list of server side configuration, an exception will be raised and returned it back to the client.

But if ``client_keys`` is set to ``None`` or not setted, ``access_key`` will not be validated by the server. 

Access Log Middleware
^^^^^^^^^^^^^^^^^^^^^

This is a default middleware.

As a RPC system, we want to save the access log for monitoring and analyzing.
All the services in one physical machine will share on logfile::

    '%(access_key)s - [%(asctime)s] - %(message)s'   

If client don't send ``access_key`` in the header, ``access_key`` will leave to ``None``::

    None - [2014-12-18 13:33:16,433] - "MySrv" - "foo" - OK - 1ms


Disable Middlewares
-------------------

The middlewares will be applied to all the servers and clients by default. If you don't want to use the middlewares, just set ``middlewares`` to ``None``::

    app = Zask(__name__)
    rpc = ZeroRPC(app, middlewares=None)

Or set a new context to the Server/Client during the runtime::

    app = Zask(__name__)
    rpc = ZeroRPC(app, middlewares=[CONFIG_ENDPOINT_MIDDLEWARE])

    default_context = zerorpc.Context().get_instance()
    srv = rpc.Server(Srv(), context=default_context)
    client = rpc.Client(context=default_context)

# -*- coding: utf-8 -*-

from testutils import random_ipc_endpoint
from zask import Zask, _request_ctx
from zask.ext import sqlalchemy
from zask.ext.zerorpc import *


def testing_scope_session():
    app = Zask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
    app.config['DEBUG'] = False
    db = sqlalchemy.SQLAlchemy(app)

    endpoint = random_ipc_endpoint()
    rpc = ZeroRPC(app, middlewares=None)
    rpc.register_middleware(sqlalchemy.SessionMiddleware(db))

    class Foo(object):

        def create_foo(self, ctx):
            ctx2 = _request_ctx.get_request_cxt()
            assert ctx == ctx2

    class Srv(rpc.Server):

        def get_session(self):
            ctx = _request_ctx.get_request_cxt()
            foo = Foo()
            foo.create_foo(ctx)

            return str(db.session())

    srv = Srv(pool_size=1)
    srv.bind(endpoint)
    gevent.spawn(srv.run)

    client = rpc.Client(endpoint)
    session1 = client.get_session(async=True)
    session2 = client.get_session(async=True)

    assert session1.get() != session2.get()

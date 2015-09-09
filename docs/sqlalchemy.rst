Zask-SQLAlchemy
===============

If you are not familiar with Flask-SQLAlchemy, the extention improves SqlAlchemy in several ways.

1. Bind with specific framework to make it easy to use
2. Contains all :mod:`sqlalchemy` and :mod:`sqlalchemy.orm` functions in one object
3. Add an amazing python descriptor to the object, which make it super cool to query data
4. Dynamic database bind depend on multiple bind configures.

As the same reason of why not just use Flask, we can't use Flask-SQLAlchemy directly.

Differents between Flask-SQLAlchemy:

1. Default ``scopefunc`` is ``gevent.getcurrent``
2. No signal session
3. No query record
4. No pagination and HTTP headers, e.g. ``get_or_404``
5. No difference between app bound and not bound

But the usage of Zask-SQLAlchemy is quite similar with Flask-SQLAlchemy. So the following of this section is just a copy from Flask-SQLAlchemy.

A Minimal Application
---------------------

The :class:`SQLAlchemy` provides a class called Model that is a declarative base which can be used to models::

    from zask import Zask
    from zask.ext.sqlalchemy import SQLAlchemy

    app = Zask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
    db = SQLAlchemy(app)

    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True)
        email = db.Column(db.String(120), unique=True)

        def __init__(self, username, email):
            self.username = username
            self.email = email

        def __repr__(self):
            return '<User %r>' % self.username

To create the initial database, just import the `db` object from an
interactive Python shell and run the
:meth:`SQLAlchemy.create_all` method to create the
tables and database:

>>> from yourapplication import db
>>> db.create_all()

Boom, and there is your database.  Now to create some users:

>>> from yourapplication import User
>>> admin = User('admin', 'admin@example.com')
>>> guest = User('guest', 'guest@example.com')

But they are not yet in the database, so let's make sure they are:

>>> db.session.add(admin)
>>> db.session.add(guest)
>>> db.session.commit()

Accessing the data in database is easy as a pie:

>>> users = User.query.all()
[<User u'admin'>, <User u'guest'>]
>>> admin = User.query.filter_by(username='admin').first()
<User u'admin'>

Scope Session with ZeroRPC
--------------------------

Session in Zask is separated by greenlet. There is a middleware for clear session automatically::

    from zask import Zask
    from zask.ext.sqlalchemy import SQLAlchemy, SessionMiddleware
    from zask.ext.zerorpc import ZeroRPC
    
    app = Zask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
    db = SQLAlchemy(app)
    rpc = ZeroRPC(app)
    rpc.register_middleware(SessionMiddleware(db))


Simple Relationships
--------------------

SQLAlchemy connects to relational databases and what relational databases
are really good at are relations.  As such, we shall have an example of an
application that uses two tables that have a relationship to each other::


    from datetime import datetime


    class Post(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(80))
        body = db.Column(db.Text)
        pub_date = db.Column(db.DateTime)

        category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
        category = db.relationship('Category',
            backref=db.backref('posts', lazy='dynamic'))

        def __init__(self, title, body, category, pub_date=None):
            self.title = title
            self.body = body
            if pub_date is None:
                pub_date = datetime.utcnow()
            self.pub_date = pub_date
            self.category = category

        def __repr__(self):
            return '<Post %r>' % self.title


    class Category(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(50))

        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return '<Category %r>' % self.name

First let's create some objects:

>>> py = Category('Python')
>>> p = Post('Hello Python!', 'Python is pretty cool', py)
>>> db.session.add(py)
>>> db.session.add(p)

Now because we declared `posts` as dynamic relationship in the backref
it shows up as query:

>>> py.posts
<sqlalchemy.orm.dynamic.AppenderBaseQuery object at 0x1027d37d0>

It behaves like a regular query object so we can ask it for all posts that
are associated with our test “Python” category:

>>> py.posts.all()
[<Post 'Hello Python!'>]

Multiple Databases with Binds
-----------------------------

Zask-SQLAlchemy can easily connect to multiple
databases.  To achieve that it preconfigures SQLAlchemy to support
multiple “binds”.

What are binds?  In SQLAlchemy speak a bind is something that can execute
SQL statements and is usually a connection or engine.  In Flask-SQLAlchemy
binds are always engines that are created for you automatically behind the
scenes.  Each of these engines is then associated with a short key (the
bind key).  This key is then used at model declaration time to assocate a
model with a specific engine.

If no bind key is specified for a model the default connection is used
instead (as configured by ``SQLALCHEMY_DATABASE_URI``).

Example Configuration
^^^^^^^^^^^^^^^^^^^^^

The following configuration declares three database connections.  The
special default one as well as two others named `users` (for the users)
and `appmeta` (which connects to a sqlite database for read only access to
some data the application provides internally)::

    SQLALCHEMY_DATABASE_URI = 'postgres://localhost/main'
    SQLALCHEMY_BINDS = {
        'users':        'mysqldb://localhost/users',
        'appmeta':      'sqlite:////path/to/appmeta.db'
    }

Creating and Dropping Tables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :meth:`SQLAlchemy.create_all` and :meth:`SQLAlchemy.drop_all` methods
by default operate on all declared binds, including the default one.  This
behavior can be customized by providing the `bind` parameter.  It takes
either a single bind name, ``'__all__'`` to refer to all binds or a list
of binds.  The default bind (``SQLALCHEMY_DATABASE_URI``) is named `None`:

>>> db.create_all()
>>> db.create_all(bind=['users'])
>>> db.create_all(bind='appmeta')
>>> db.drop_all(bind=None)

Referring to Binds
^^^^^^^^^^^^^^^^^^

If you declare a model you can specify the bind to use with the
:attr:`~Model.__bind_key__` attribute::

    class User(db.Model):
        __bind_key__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True)

Internally the bind key is stored in the table's `info` dictionary as
``'bind_key'``.  This is important to know because when you want to create
a table object directly you will have to put it in there::

    user_favorites = db.Table('user_favorites',
        db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
        db.Column('message_id', db.Integer, db.ForeignKey('message.id')),
        info={'bind_key': 'users'}
    )

If you specified the `__bind_key__` on your models you can use them exactly the
way you are used to.  The model connects to the specified database connection 
itself.








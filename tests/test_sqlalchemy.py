# -*- coding: utf-8 -*-

import atexit
import unittest
from datetime import datetime

from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query as BaseQuery
from zask import Zask
from zask.ext import sqlalchemy


def make_todo_model(db):
    class Todo(db.Model):
        __tablename__ = 'todos'
        id = db.Column('todo_id', db.Integer, primary_key=True)
        title = db.Column(db.String(60))
        text = db.Column(db.String)
        done = db.Column(db.Boolean)
        pub_date = db.Column(db.DateTime)

        def __init__(self, title, text):
            self.title = title
            self.text = text
            self.done = False
            self.pub_date = datetime.utcnow()
    return Todo


class BasicSQLAlchemyTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Zask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        self.db = sqlalchemy.SQLAlchemy(self.app)

        self.Todo = make_todo_model(self.db)
        self.db.create_all()

    def tearDown(self):
        self.db.drop_all()

    def test_basic_insert(self):

        self.db.session.add(self.Todo('First Item', 'The text'))
        self.db.session.add(self.Todo('2nd Item', 'The text'))
        self.db.session.commit()

        rv = '\n'.join(x.title for x in self.Todo.query.all())
        self.assertEqual(rv, 'First Item\n2nd Item')

    def test_helper_api(self):
        self.assertEqual(self.db.metadata, self.db.Model.metadata)


class TestAppBound(unittest.TestCase):

    def setUp(self):
        self.app = Zask(__name__)
        self.app.config['SQLALCHEMY_ENGINE'] = 'sqlite://'

    def test_no_app_bound(self):
        db = sqlalchemy.SQLAlchemy()
        db.init_app(self.app)
        Todo = make_todo_model(db)

        db.create_all()
        todo = Todo('Test', 'test')
        db.session.add(todo)
        db.session.commit()
        self.assertEqual(len(Todo.query.all()), 1)
        db.drop_all()

    def test_app_bound(self):
        db = sqlalchemy.SQLAlchemy(self.app)
        Todo = make_todo_model(db)

        db.create_all()
        todo = Todo('Test', 'test')
        db.session.add(todo)
        db.session.commit()
        self.assertEqual(len(Todo.query.all()), 1)
        db.drop_all()


class TablenameTestCase(unittest.TestCase):

    def test_name(self):
        app = Zask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db = sqlalchemy.SQLAlchemy(app)

        class FOOBar(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        class BazBar(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        class Ham(db.Model):
            __tablename__ = 'spam'
            id = db.Column(db.Integer, primary_key=True)

        self.assertEqual(FOOBar.__tablename__, 'foo_bar')
        self.assertEqual(BazBar.__tablename__, 'baz_bar')
        self.assertEqual(Ham.__tablename__, 'spam')

    def test_single_name(self):
        """Single table inheritance should not set a new name."""

        app = Zask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db = sqlalchemy.SQLAlchemy(app)

        class Duck(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        class Mallard(Duck):
            pass

        self.assertEqual(Mallard.__tablename__, 'duck')

    def test_joined_name(self):
        """Model has a separate primary key; it should set a new name."""

        app = Zask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db = sqlalchemy.SQLAlchemy(app)

        class Duck(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        class Donald(Duck):
            id = db.Column(
                db.Integer, db.ForeignKey(
                    Duck.id), primary_key=True)

        self.assertEqual(Donald.__tablename__, 'donald')

    def test_mixin_name(self):
        """Primary key provided by mixin should still allow
           model to set tablename."""

        app = Zask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db = sqlalchemy.SQLAlchemy(app)

        class Base(object):
            id = db.Column(db.Integer, primary_key=True)

        class Duck(Base, db.Model):
            pass

        self.assertFalse(hasattr(Base, '__tablename__'))
        self.assertEqual(Duck.__tablename__, 'duck')

    def test_abstract_name(self):
        """Abstract model should not set a name.
           Subclass should set a name."""

        app = Zask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db = sqlalchemy.SQLAlchemy(app)

        class Base(db.Model):
            __abstract__ = True
            id = db.Column(db.Integer, primary_key=True)

        class Duck(Base):
            pass

        self.assertFalse(hasattr(Base, '__tablename__'))
        self.assertEqual(Duck.__tablename__, 'duck')

    def test_complex_inheritance(self):
        """Joined table inheritance,
           but the new primary key is provided by a mixin,
           not directly on the class."""

        app = Zask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db = sqlalchemy.SQLAlchemy(app)

        class Duck(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        class IdMixin(object):

            @declared_attr
            def id(cls):
                return db.Column(
                    db.Integer, db.ForeignKey(
                        Duck.id), primary_key=True)

        class RubberDuck(IdMixin, Duck):
            pass

        self.assertEqual(RubberDuck.__tablename__, 'rubber_duck')


class BindsTestCase(unittest.TestCase):

    def test_basic_binds(self):
        import tempfile
        _, db1 = tempfile.mkstemp()
        _, db2 = tempfile.mkstemp()

        def _remove_files():
            import os
            try:
                os.remove(db1)
                os.remove(db2)
            except IOError:
                pass
        atexit.register(_remove_files)

        app = Zask(__name__)
        app.config['SQLALCHEMY_ENGINE'] = 'sqlite://'
        app.config['SQLALCHEMY_BINDS'] = {
            'foo': 'sqlite:///' + db1,
            'bar': 'sqlite:///' + db2
        }
        db = sqlalchemy.SQLAlchemy(app)

        class Foo(db.Model):
            __bind_key__ = 'foo'
            __table_args__ = {"info": {"bind_key": "foo"}}
            id = db.Column(db.Integer, primary_key=True)

        class Bar(db.Model):
            __bind_key__ = 'bar'
            id = db.Column(db.Integer, primary_key=True)

        class Baz(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        db.create_all()

        # simple way to check if the engines are looked up properly
        self.assertEqual(db.get_engine(app, None), db.engine)
        for key in 'foo', 'bar':
            engine = db.get_engine(app, key)
            connector = app.extensions['sqlalchemy'].connectors[key]
            self.assertEqual(engine, connector.get_engine())
            self.assertEqual(str(engine.url),
                             app.config['SQLALCHEMY_BINDS'][key])

        # do the models have the correct engines?
        self.assertEqual(db.metadata.tables['foo'].info['bind_key'], 'foo')
        self.assertEqual(db.metadata.tables['bar'].info['bind_key'], 'bar')
        self.assertEqual(db.metadata.tables['baz'].info.get('bind_key'), None)

        # see the tables created in an engine
        metadata = db.MetaData()
        metadata.reflect(bind=db.get_engine(app, 'foo'))
        self.assertEqual(len(metadata.tables), 1)
        self.assertTrue('foo' in metadata.tables)

        metadata = db.MetaData()
        metadata.reflect(bind=db.get_engine(app, 'bar'))
        self.assertEqual(len(metadata.tables), 1)
        self.assertTrue('bar' in metadata.tables)

        metadata = db.MetaData()
        metadata.reflect(bind=db.get_engine(app))
        self.assertEqual(len(metadata.tables), 1)
        self.assertTrue('baz' in metadata.tables)

        # do the session have the right binds set?
        self.assertEqual(db.get_binds(app), {
            Foo.__table__: db.get_engine(app, 'foo'),
            Bar.__table__: db.get_engine(app, 'bar'),
            Baz.__table__: db.get_engine(app, None)
        })

        # do the models in the same session?
        foo = Foo()
        bar = Bar()
        baz = Baz()
        db.session.add(foo)
        db.session.add(bar)
        db.session.add(baz)
        assert foo in db.session
        assert bar in db.session
        assert baz in db.session

        db.drop_all()


class DefaultQueryClassTestCase(unittest.TestCase):

    def test_default_query_class(self):
        app = Zask(__name__)
        app.config['SQLALCHEMY_ENGINE'] = 'sqlite://'
        app.config['TESTING'] = True
        db = sqlalchemy.SQLAlchemy(app)

        class Parent(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            children = db.relationship(
                "Child", backref="parents", lazy='dynamic')

        class Child(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'))
        p = Parent()
        c = Child()
        c.parent = p
        self.assertEqual(type(Parent.query), BaseQuery)
        self.assertEqual(type(Child.query), BaseQuery)
        self.assertTrue(isinstance(p.children, BaseQuery))


class SessionScopingTestCase(unittest.TestCase):

    def test_default_session_scoping(self):
        app = Zask(__name__)
        app.config['SQLALCHEMY_ENGINE'] = 'sqlite://'
        db = sqlalchemy.SQLAlchemy(app)

        class FOOBar(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        db.create_all()

        fb = FOOBar()
        db.session.add(fb)
        assert fb in db.session

        db.drop_all()

    def test_session_scoping_changing(self):
        app = Zask(__name__)
        app.config['SQLALCHEMY_ENGINE'] = 'sqlite://'

        def scopefunc():
            return id(dict())

        db = sqlalchemy.SQLAlchemy(
            app, session_options=dict(
                scopefunc=scopefunc))

        class FOOBar(db.Model):
            id = db.Column(db.Integer, primary_key=True)

        db.create_all()

        fb = FOOBar()
        db.session.add(fb)
        assert fb not in db.session
        # ^ because a new scope is generated on each call

        db.drop_all()

if __name__ == '__main__':
    unittest.main()

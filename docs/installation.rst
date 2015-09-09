.. _installation:

Installation
=================

Libzmq
------

Ensure `libzmq`_ installed.

.. _libzmq: http://zeromq.org/docs:source-git

Virtualenv and VE
-----------------

Virtualenv now is considered as best practice of developping Python project::

    $ virtualenv .virutualenv
    $ . .virtualenv/bin/activate

`VE`_ is a perfect friend to work with virtualenv. VE will activate any virtualenv in the current path.
You can run any python command with a ``ve`` prefix::

    $ ve python setup.py develop
    $ ve pip install foo
    $ ve pip freeze

.. _VE: https://github.com/erning/ve


Install from setuptools
-----------------------

Add dependence in your ``setup.py``::

    setup(
        # jump other params
        ...

        install_requires = [
            'zask==1.0.dev'
        ],
        dependency_links=[
            "git+ssh://git@github.com/j-5/zask.git@0.1.dev#egg=zask-1.0.dev"
        ]
    )

You can use zask in your project after run ``ve python setup.py develop``::

    import zask


Build from source code
----------------------

If you want to dive into zask, run::

    $ git clone http://github.com/j-5/zask.git
    $ cd zask
    $ virtualenv .virtualenv
    $ ve python setup.py develop


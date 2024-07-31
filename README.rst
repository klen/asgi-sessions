ASGI-Sessions
#############

.. _description:

**asgi-sessions** -- Cookie-Based HTTP sessions for ASGI applications (Asyncio_ / Trio_, / Curio_)

.. _badges:

.. image:: https://github.com/klen/asgi-sessions/workflows/tests/badge.svg
    :target: https://github.com/klen/asgi-sessions/actions
    :alt: Tests Status

.. image:: https://img.shields.io/pypi/v/asgi-sessions
    :target: https://pypi.org/project/asgi-sessions/
    :alt: PYPI Version

.. image:: https://img.shields.io/pypi/pyversions/asgi-sessions
    :target: https://pypi.org/project/asgi-sessions/
    :alt: Python Versions

.. _contents:

.. contents::

Features
========

* Supports base64 sessions
* Supports ``JWT`` signed sessions
* Supports ``Fernet`` encrypted sessions

.. _requirements:

Requirements
=============

- python >= 3.9

.. _installation:

Installation
=============

**asgi-sessions** should be installed using pip: ::

    pip install asgi-sessions

To install optional ``JWT``, ``Fernet`` support: ::

    pip install asgi-sessions[jwt]
    pip install asgi-sessions[fernet]

.. _usage:

Usage
=====

Common ASGI applications:

.. code:: python

    from asgi_sessions import SessionMiddleware


    async def my_app(scope, receive, send):
        """Read session and get the current user data from it or from request query."""
        # The middleware puts a session into scope['session]
        session = scope['session']

        status, headers = 200, []
        if scope['query_string']:
            # Store any information inside the session
            session['user'] = scope['query_string'].decode()
            status, headers = 307, [(b"location", b"/")]

        # Read a stored info from the session
        user = (session.get('user') or 'anonymous').title().encode()

        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": b"Hello %s" % user})

    app = SessionMiddleware(my_app, session_type='jwt', secret_key="sessions-secret")

    # http GET / -> Hello Anonymous
    # http GET /?tom -> Hello Tom
    # http GET / -> Hello Tom


As ASGI-Tools Internal middleware

.. code:: python

    from asgi_tools import App
    from asgi_sessions import SessionMiddleware

    app = App()
    app.middleware(SessionMiddleware.setup(session_type='jwt', secret_key='SESSION-SECRET'))

    @app.route('/')
    async def index(request):
        user = request.session.get('user', 'Anonymous')
        return 'Hello %s' % user.title()

    @app.route('/login/{user}')
    async def login(request):
        request.session['user'] = request.path_params.get('user', 'Anonymous')
        return 'Done'

    @app.route('/logout')
    async def logout(request, *args):
        del request.session['user']
        return 'Done'

    # http GET / -> Hello Anonymous
    # http GET /login/tom -> Done
    # http GET / -> Hello Tom
    # http GET /logout -> Done
    # http GET / -> Hello Anonymous


Options
========

.. code:: python

   from asgi_sessions import SessionMiddleware

   app = SessionMiddleware(

        # Your ASGI application
        app,

        # Session type (base64|jwt|fernet)
        session_type="base64",

        # Secret Key for the session (required for JWT/Fernet sessions)
        secret_key=None,

        # Cookie name to keep the session (optional)
        cookie_name='session',

        # Cookie max age (in seconds) (optional)
        max_age=14 * 24 * 3600,

        # Cookie samesite (optional)  # Python 3.8+ only
        samesite='lax',

        # Cookie secure (https only) (optional)
        secure=False,

   )

.. _bugtracker:

Bug tracker
===========

If you have any suggestions, bug reports or
annoyances please report them to the issue tracker
at https://github.com/klen/asgi-sessions/issues

.. _contributing:

Contributing
============

Development of the project happens at: https://github.com/klen/asgi-sessions

.. _license:

License
========

Licensed under a `MIT license`_.


.. _links:

.. _MIT license: http://opensource.org/licenses/MIT
.. _Asyncio: https://docs.python.org/3/library/asyncio.html
.. _klen: https://github.com/klen
.. _Trio: https://trio.readthedocs.io/en/stable/
.. _Curio: https://curio.readthedocs.io/en/latest/


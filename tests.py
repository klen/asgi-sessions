import pytest

from asgi_tools.tests import ASGITestClient


SECRET = 'SECRET78901234567890123456789012'


def test_session():
    from asgi_sessions import Session

    session = Session()
    assert not session.modified

    session['user'] = 'john'
    assert session.modified

    token = session.encode()
    assert token

    session = Session(token)
    assert session['user'] == 'john'
    assert not session.modified
    del session['user']
    assert session.modified

    session = Session('invalid', uid=12)
    assert session
    assert session['uid'] == 12
    session['data'] = 42

    data = session.pop('data')
    assert data == 42


def test_session_jwt():
    from asgi_sessions import SessionJWT as Session

    session = Session(secret=SECRET)
    assert not session.modified

    session['user'] = 'john'
    assert session.modified

    token = session.encode()
    assert token

    session = Session(token, secret=SECRET)
    assert session['user'] == 'john'
    assert not session.modified
    del session['user']
    assert session.modified


def test_session_fernet():
    from asgi_sessions import SessionFernet as Session

    session = Session(secret=SECRET)
    assert not session.modified

    session['user'] = 'john'
    assert session.modified

    token = session.encode()
    assert token

    session = Session(token, secret=SECRET)
    assert session['user'] == 'john'
    assert not session.modified
    del session['user']
    assert session.modified


@pytest.mark.parametrize('ses_type', ['jwt', 'fernet', 'base64'])
async def test_base(ses_type):
    from asgi_sessions import SessionMiddleware

    async def my_app(scope, receive, send):
        """Read session and get the current user data from it or from request query."""
        session = scope['session']
        status, headers = 200, []
        if scope['query_string']:
            session['user'] = scope['query_string'].decode()
            status, headers = 307, [(b"location", b"/")]

        user = (session.get('user') or 'anonymous').title().encode()
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": b"Hello %s" % user, "more_body": False})

    app = SessionMiddleware(my_app, secret_key=SECRET, session_type=ses_type)
    client = ASGITestClient(app)

    res = await client.get('/')
    assert res.status_code == 200
    assert await res.text() == "Hello Anonymous"

    res = await client.get('/?tom')
    assert await res.text() == "Hello Tom"

    res = await client.get('/?mike')
    assert await res.text() == "Hello Mike"

    res = await client.get('/')
    assert await res.text() == "Hello Mike"


@pytest.mark.parametrize('ses_type', ['jwt', 'fernet', 'base64'])
async def test_asgi_tools_external(ses_type):
    from asgi_tools import App
    from asgi_sessions import SessionMiddleware

    app = App()

    @app.route('/')
    async def index(request):
        session = request['session']
        user = session.get('user', 'guest')
        return 'Hello %s' % user

    @app.route('/login/{user}')
    async def login(request):
        session = request['session']
        session['user'] = request.path_params.get('user', 'guest')
        return "Done"

    @app.route('/logout')
    async def logout(request):
        session = request['session']
        session.pop('user')
        return "Done"

    app = SessionMiddleware(app, secret_key=SECRET, session_type=ses_type)
    client = ASGITestClient(app)

    res = await client.get('/')
    assert await res.text() == "Hello guest"

    res = await client.get('/login/john')
    assert await res.text() == "Done"
    assert client.cookies['session']

    res = await client.get('/')
    assert await res.text() == "Hello john"

    res = await client.get('/logout')
    assert await res.text() == "Done"

    res = await client.get('/')
    assert await res.text() == "Hello guest"


@pytest.mark.parametrize('ses_type', ['jwt', 'fernet', 'base64'])
async def test_asgi_tools_internal(ses_type):
    from asgi_tools import App
    from asgi_sessions import SessionMiddleware

    app = App()
    app.middleware(SessionMiddleware.setup(secret_key=SECRET, session_type=ses_type))
    client = ASGITestClient(app)

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

    res = await client.get('/')
    assert await res.text() == "Hello Anonymous"

    res = await client.get('/login/tom')
    assert await res.text() == "Done"
    assert client.cookies['session']

    res = await client.get('/')
    assert await res.text() == "Hello Tom"

    res = await client.get('/logout')
    assert await res.text() == "Done"

    res = await client.get('/')
    assert await res.text() == "Hello Anonymous"

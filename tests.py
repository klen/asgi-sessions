import pytest
from asgi_tools.tests import ASGITestClient


@pytest.fixture(params=[
    pytest.param('asyncio'),
    pytest.param('trio'),
    pytest.param('curio'),
], autouse=True)
def anyio_backend(request):
    return request.param


def test_session():
    from asgi_sessions import Session

    session = Session('SECRET')
    assert session.pure
    session['user'] = 'john'
    assert not session.pure

    token = session.encode()
    assert token

    session = Session('SECRET', token)
    assert session['user'] == 'john'
    assert session.pure
    del session['user']
    assert not session.pure

    session = Session('SECRET', 'invalid', uid=12)
    assert session
    session['data'] = 42

    data = session.pop('data')
    assert data == 42


async def test_base():
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

    app = SessionMiddleware(my_app, secret_key="sessions-secret")
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


async def test_asgi_tools_external():
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

    app = SessionMiddleware(app, secret_key='SESSION-SECRET')
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


async def test_asgi_tools_internal():
    from asgi_tools import App
    from asgi_sessions import SessionMiddleware

    app = App()
    app.middleware(SessionMiddleware.setup(secret_key='SESSION-SECRET'))
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

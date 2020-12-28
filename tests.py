import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


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
        await send({"type": "http.response.body", "body": b"Hello %s" % user})

    app = SessionMiddleware(my_app, secret_key="sessions-secret")

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        res = await client.get('/')
        assert res.status_code == 200
        assert res.text == "Hello Anonymous"

        res = await client.get('/?tom')
        assert res.text == "Hello Tom"

        res = await client.get('/?mike')
        assert res.text == "Hello Mike"

        res = await client.get('/')
        assert res.text == "Hello Mike"


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
    async def login(request, user='guest'):
        session = request['session']
        session['user'] = user
        return "Done"

    @app.route('/logout')
    async def logout(request, *args):
        session = request['session']
        session.pop('user')
        return "Done"

    app = SessionMiddleware(app, secret_key='SESSION-SECRET')

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        res = await client.get('/')
        assert res.text == "Hello guest"

        res = await client.get('/login/john')
        assert res.text == "Done"
        assert client.cookies['session']

        res = await client.get('/')
        assert res.text == "Hello john"

        res = await client.get('/logout')
        assert res.text == "Done"

        res = await client.get('/')
        assert res.text == "Hello guest"


async def test_asgi_tools_internal():
    from asgi_tools import App
    from asgi_sessions import SessionMiddleware

    app = App()
    app.middleware(SessionMiddleware.setup(secret_key='SESSION-SECRET'))

    @app.route('/')
    async def index(request):
        session = request['session']
        user = session.get('user', 'Anonymous')
        return 'Hello %s' % user.title()

    @app.route('/login/{user}')
    async def login(request, user='anonymous'):
        session = request['session']
        session['user'] = user
        return 'Done'

    @app.route('/logout')
    async def logout(request, *args):
        session = request['session']
        del session['user']
        return 'Done'

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        res = await client.get('/')
        assert res.text == "Hello Anonymous"

        res = await client.get('/login/tom')
        assert res.text == "Done"
        assert client.cookies['session']

        res = await client.get('/')
        assert res.text == "Hello Tom"

        res = await client.get('/logout')
        assert res.text == "Done"

        res = await client.get('/')
        assert res.text == "Hello Anonymous"

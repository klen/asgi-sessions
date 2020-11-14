__version__ = "0.0.2"
__license__ = "MIT"

from http import cookies

from asgi_tools import Request, Response
from asgi_tools.middleware import BaseMiddeware
import jwt


class Session(dict):

    def __init__(self, secret_key, token=None, **payload):
        self.secret_key = secret_key

        if token:
            try:
                self.update(jwt.decode(token, key=self.secret_key))
            except jwt.DecodeError:
                return {}

        if payload:
            self.update(payload)

        self.pure = True

    def encode(self, **kwargs):
        return jwt.encode(self, key=self.secret_key).decode()

    def cookie(self, cookie_name, cookie_params):
        morsel = cookies.Morsel()
        value = self.encode()
        morsel.set(cookie_name, value, value)
        for k in cookie_params:
            morsel[k] = cookie_params[k]
        return morsel.OutputString()

    def __setitem__(self, name, value):
        self.pure = self.get(name) == value
        dict.__setitem__(self, name, value)

    def __delitem__(self, name):
        self.pure = name not in self
        dict.__delitem__(self, name)

    def clear(self):
        self.pure = not self
        dict.clear(self)

    def pop(self, name, default=None):
        self.pure = not self
        dict.clear(self)

    def update(self, value):
        self.pure = not value
        dict.update(self, value)


class SessionMiddleware(BaseMiddeware):
    """Support sessions."""

    def __init__(
            self, app, secret_key=None, cookie_name='session', max_age=14 * 24 * 3600,
            samesite='lax', secure=False, **kwargs):
        """Init the middleware."""
        super(SessionMiddleware, self).__init__(app, **kwargs)
        assert secret_key, "secret_key is required"
        self.secret_key = secret_key
        self.cookie_name = cookie_name

        self.cookie_params = {'path': '/'}
        if max_age:
            self.cookie_params['max-age'] = max_age
        if samesite:
            self.cookie_params['samesite'] = samesite
        if secure:
            self.cookie_params['secure'] = secure

    async def process(self, scope, receive, send):
        """Load/save the sessions."""

        # Support asgi_tools.RequestMiddleware
        if isinstance(scope, Request):
            request = scope
        else:
            request = scope.get('request') or Request(scope)

        session = Session(self.secret_key, token=request.cookies.get(self.cookie_name))
        scope['session'] = session

        # Common ASGI Applications
        def send_wrapper(message):
            """Inject sessions cookie."""
            if not session.pure and message["type"] == "http.response.start":
                message['headers'].append((
                    b'Set-Cookie',
                    session.cookie(self.cookie_name, self.cookie_params).encode(),
                ))

            return send(message)

        # ASGI-Tools internal middleware
        response = await self.app(scope, receive, send_wrapper)
        if response and isinstance(response, Response) and not session.pure:
            response._headers['Set-Cookie'] = session.cookie(
                self.cookie_name, self.cookie_params)

        return response

"""Support cookie-encrypted sessions for ASGI applications."""

__version__ = "0.4.2"
__license__ = "MIT"

import typing as t
from http import cookies

from asgi_tools import Request, Response
from asgi_tools.middleware import BaseMiddeware, ASGIApp
from asgi_tools.types import JSONType, Scope, Receive, Send
import jwt


__all__ = 'Session', 'SessionMiddleware'


class Session(dict):
    """Keep/update sessions data."""

    def __init__(self, secret_key: str, token: str = None, **payload):
        """Initialize the container."""
        self.secret_key = secret_key

        if token:
            try:
                self.update(jwt.decode(token, key=self.secret_key, algorithms=['HS256']))
            except jwt.DecodeError:
                pass

        if payload:
            self.update(payload)

        self.pure = True

    def __setitem__(self, name: str, value: JSONType):
        """Store the value and check that the session is pure."""
        self.pure = self.get(name) == value
        dict.__setitem__(self, name, value)

    def __delitem__(self, name: str):
        """Delete the value and check that the session is pure."""
        self.pure = name not in self
        dict.__delitem__(self, name)

    def encode(self) -> str:
        """Encode the session's data."""
        token = jwt.encode(self, key=self.secret_key, algorithm='HS256')
        # Support JWT<2 (Remove me after 2022-01-01)
        if isinstance(token, bytes):
            token = token.decode()
        return token

    def cookie(self, cookie_name: str, cookie_params: t.Dict) -> str:
        """Render the data as a cookie string."""
        morsel: cookies.Morsel = cookies.Morsel()
        value = self.encode()
        morsel.set(cookie_name, value, value)
        for k in cookie_params:
            morsel[k] = cookie_params[k]
        return morsel.OutputString()

    def clear(self) -> None:
        self.pure = not self
        return dict.clear(self)

    def pop(self, name: str, default=None) -> JSONType:
        self.pure = not self
        return dict.pop(self, name, default)

    def update(self, value: t.Dict[str, JSONType]):  # type: ignore
        self.pure = not value
        return dict.update(self, value)


class SessionMiddleware(BaseMiddeware):
    """Support sessions."""

    def __init__(
            self, app: ASGIApp, secret_key: str = None, cookie_name: str = 'session',
            max_age: int = 14 * 24 * 3600, samesite: str = 'lax', secure: bool = False):
        """Init the middleware."""
        super(SessionMiddleware, self).__init__(app)
        assert secret_key, "secret_key is required"
        self.secret_key = secret_key
        self.cookie_name = cookie_name

        self.cookie_params: t.Dict[str, t.Any] = {'path': '/'}
        if max_age:
            self.cookie_params['max-age'] = max_age
        if samesite:
            self.cookie_params['samesite'] = samesite
        if secure:
            self.cookie_params['secure'] = secure

    async def __process__(self, scope: t.Union[Scope, Request], receive: Receive, send: Send):
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

        # Support ASGI-Tools Responses
        response = await self.app(scope, receive, send_wrapper)
        if response and isinstance(response, Response) and not session.pure:
            response.headers['Set-Cookie'] = session.cookie(self.cookie_name, self.cookie_params)

        return response

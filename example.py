from asgi_tools import RedirectResponse, AppMiddleware
from asgi_sessions import SessionMiddleware


app = SessionMiddleware(AppMiddleware(), secret_key='SESSION-SECRET')


@app.route('/login')
async def login(request, *args):
    data = await request.form()
    session = request['session']
    session['user'] = data.get('user')
    return RedirectResponse('/')


@app.route('/logout')
async def logout(scope, *args):
    session = scope['session']
    session.pop('user', None)
    return RedirectResponse('/')


@app.route('/')
async def index(request, *args):
    session = request['session']
    user = session.get('user')
    return f"""
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css">
    <div class="container p-3">
        <p class="lead">
            A simple example to show how <span class="font-weight-bold">ASGI-Sessions</span> works.
            <br/>
            Store/erase an username in the secured cookies session.
        </p>
        <h2>Hello {user or 'anonymous'}</h2>
        <form action="/login" method="post">
            <div class="form-group">
                <label for="user">Login as</label>
                <input name="user" placeholder="username (enter)" />
            </div>
            <button class="btn btn-primary" type="submit">Login</button>
            <button onclick="window.location='/logout'" type="button"
                    class="btn btn-danger" { user or 'disabled="disabled"' }">Logout</button>
        </form>
    </div>
"""

import logging
from os import read
from sqlite3 import Connection
from typing import cast

from flask import Blueprint, Response, redirect, render_template, request

from raphson_mp import auth, db, jsonw
from raphson_mp.auth import AuthError, User
from raphson_mp.decorators import route

log = logging.getLogger(__name__)
bp = Blueprint('auth', __name__, url_prefix='/auth')


def handle_auth_error(err: AuthError):
    """
    Display permission denied error page with reason, or redirect to login page
    """
    if err.redirect:
        return redirect('/auth/login', code=303)

    return Response(render_template('403.jinja2', reason=err.reason.message), 403)


@route(bp, '/login', methods=['GET', 'POST'], write=True, public=True)
def route_login():
    """
    Login route. Serve login page for GET requests, and accepts password input for POST requests.
    If the provided password is invalid, the login template is rendered with invalid_password=True
    """
    if request.method == 'GET':
        try:
            with db.connect(read_only=True) as conn:
                auth.verify_auth_cookie(conn)
            # User is already logged in
            return redirect('/', code=303)
        except AuthError:
            pass

        return render_template('login.jinja2', invalid_password=False)

    username: str = cast(str, request.json['username']) if request.is_json else request.form['username']
    password: str = cast(str, request.json['password']) if request.is_json else request.form['password']

    with db.connect() as conn:
        session = auth.log_in(conn, username, password)

    if session is None:
        if request.is_json:
            return Response(None, 403)

        return render_template('login.jinja2', invalid_password=True)

    if request.is_json:
        return {'token': session.token, 'csrf': session.csrf_token}

    response = redirect('/', code=303)
    session.set_cookie(response)
    return response


@route(bp, '/get_csrf')
def route_get_csrf(_conn: Connection, user: User):
    """
    Get CSRF token
    """
    response = jsonw.json_response({'token': user.csrf})
    response.cache_control.max_age = 600
    response.cache_control.private = True
    return response

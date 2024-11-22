import logging
from sqlite3 import Connection
from typing import cast

from flask import Blueprint, Response, abort, redirect, render_template, request

from raphson_mp import db, jsonw, music, packer, settings
from raphson_mp import auth
from raphson_mp.auth import StandardUser, User
from raphson_mp.decorators import route

bp = Blueprint('root', __name__, url_prefix='/')
log = logging.getLogger(__name__)


@route(bp, '', redirect_to_login=True)
def route_home(_conn: Connection, user: User):
    """
    Home page, with links to file manager and music player
    """
    return render_template('home.jinja2',
                           user_is_admin=user.admin,
                           offline_mode=settings.offline_mode)


@route(bp, 'static/js/player.js', public=True)
def route_player_js():
    """
    Concatenated javascript file for music player. Only used during development.
    """
    return Response(packer.pack(settings.static_dir / 'js' / 'player'),
                    content_type='application/javascript')


@route(bp, 'info')
def route_info(_conn: Connection, _user: User):
    """
    Information/manual page
    """
    return render_template('info.jinja2')


@route(bp, 'lastfm_callback', public=True)
def route_lastfm_callback():
    # After allowing access, last.fm sends the user to this page with an
    # authentication token. The authentication token can only be used once,
    # to obtain a session key. Session keys are stored in the database.

    # Cookies are not present here (because of cross-site redirect), so we
    # can't save the token just yet. Add another redirect step.

    auth_token = request.args['token']
    return render_template('lastfm_callback.jinja2',
                           auth_token=auth_token)


@route(bp, 'lastfm_connect', methods=['POST'], write=True, skip_csrf_check=True)
def route_lastfm_connect(conn: Connection, user: StandardUser):
    # This form does not have a CSRF token, because the user is not known
    # in the code that serves the form. Not sure how to fix this.

    from raphson_mp import lastfm

    auth_token = request.form['auth_token']
    name = lastfm.obtain_session_key(user, auth_token)

    return render_template('lastfm_connected.jinja2',
                           name=name)

@route(bp, 'lastfm_disconnect', methods=['POST'], write=True)
def route_lastfm_disconnect(conn: Connection, user: User):
    conn.execute('DELETE FROM user_lastfm WHERE user=?', (user.user_id,))
    return redirect('/account', code=303)


@route(bp, 'download_offline', redirect_to_login=True)
def route_download_offline(conn: Connection, _user: StandardUser):
    playlists = music.playlists(conn)

    return render_template('download_offline.jinja2',
                           playlists=playlists)


@route(bp, 'install')
def route_install(_conn: Connection, _user: StandardUser):
    return render_template('install.jinja2')


@route(bp, 'pwa', public=True)
def route_pwa():
    # Cannot have /player as an entrypoint directly, because for some reason the first request
    # to the start_url does not include cookies. Even a regular 302 redirect doesn't work!
    return '<meta http-equiv="refresh" content="0;URL=\'/player\'">'


@route(bp, 'csp_reports', methods=['POST'], public=True)
def route_csp_reports():
    # TODO Add rate limit
    assert request.content_type == 'application/csp-report'
    if len(request.data) > 1000:
        log.warning('Received large Content-Security-Policy: %s bytes', len(request.data))
    else:
        log.warning('Received Content-Security-Policy report: %s', jsonw.from_json(request.data))
    return Response(None, 200)


@route(bp, 'report_error', methods=['POST'], skip_csrf_check=True)
def route_error_report(_conn: Connection, _user: StandardUser):
    if not request.is_json:
        abort(400)

    if len(request.data) > 1000:
        log.warning('Received large error report: %s bytes', len(request.data))
    else:
        log.warning('Received JavaScript error: %s', request.json)
    return Response(None, 200)


# TODO add nice interface
# TODO add a way to discover this page
# TODO require user password
@route(bp, 'token', write=True)
def route_token(conn: Connection, user: StandardUser):
    token = auth.create_session(conn, user)
    return Response(token.token, status=200, mimetype='text/plain')


@route(bp, 'health_check', public=True)
def route_health_check():
    return Response('ok', content_type='text/plain')


@route(bp, ['security.txt', '.well-known/security.txt'], public=True)
def security_txt():
    content = """Contact: mailto:robin@rslot.nl
Expires: 2026-12-31T23:59:59.000Z
Preferred-Languages: en, nl
"""
    return Response(content, content_type='text/plain')

import logging

from flask import Blueprint, Response, redirect, render_template, request

from raphson_mp import auth, db, jsonw, music, packer, settings

bp = Blueprint('root', __name__, url_prefix='/')
log = logging.getLogger(__name__)


@bp.route('')
def route_home():
    """
    Home page, with links to file manager and music player
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
    return render_template('home.jinja2',
                           user_is_admin=user.admin,
                           offline_mode=settings.offline_mode)


@bp.route('static/js/player.js')
def route_player_js():
    """
    Concatenated javascript file for music player. Only used during development.
    """
    return Response(packer.pack(settings.static_dir / 'js' / 'player'),
                    content_type='application/javascript')


@bp.route('info')
def route_info():
    """
    Information/manual page
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    return render_template('info.jinja2')


@bp.route('lastfm_callback')
def route_lastfm_callback():
    # After allowing access, last.fm sends the user to this page with an
    # authentication token. The authentication token can only be used once,
    # to obtain a session key. Session keys are stored in the database.

    # Cookies are not present here (because of cross-site redirect), so we
    # can't save the token just yet. Add another redirect step.

    auth_token = request.args['token']
    return render_template('lastfm_callback.jinja2',
                           auth_token=auth_token)


@bp.route('lastfm_connect', methods=['POST'])
def route_lastfm_connect():
    from raphson_mp import lastfm

    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        # This form does not have a CSRF token, because the user is known
        # in the code that serves the form. Not sure how to fix this.
        # An attacker being able to link their last.fm account is not that bad
        # of an issue, so we'll deal with it later.
        auth_token = request.form['auth_token']
        name = lastfm.obtain_session_key(user, auth_token)
    return render_template('lastfm_connected.jinja2',
                           name=name)

@bp.route('lastfm_disconnect', methods=['POST'])
def route_lastfm_disconnect():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)
        conn.execute('DELETE FROM user_lastfm WHERE user=?',
                     (user.user_id,))
    return redirect('/account', code=303)


@bp.route('download_offline')
def route_download_offline():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        playlists = music.playlists(conn)

    return render_template('download_offline.jinja2',
                           playlists=playlists)


@bp.route('install')
def route_install():
    return render_template('install.jinja2')


@bp.route('pwa')
def route_pwa():
    # Cannot have /player as an entrypoint directly, because for some reason the first request
    # to the start_url does not include cookies. Even a regular 302 redirect doesn't work!
    return '<meta http-equiv="refresh" content="0;URL=\'/player\'">'


@bp.route('csp_reports', methods=['POST'])
def route_csp_reports():
    # TODO Add rate limit
    assert request.content_type == 'application/csp-report'
    if len(request.data) > 1000:
        log.warning('Received large Content-Security-Policy: %s bytes', len(request.data))
    else:
        log.warning('Received Content-Security-Policy report: %s', jsonw.from_json(request.data))
    return Response(None, 200)


@bp.route('health_check')
def route_health_check():
    return Response('ok', content_type='text/plain')


@bp.route('security.txt')
@bp.route('.well-known/security.txt')
def security_txt():
    content = """Contact: mailto:robin@rslot.nl
Expires: 2026-12-31T23:59:59.000Z
Preferred-Languages: en, nl
"""
    return Response(content, content_type='text/plain')

"""
Main application file, containing all Flask routes
"""
import logging
import shutil
from pathlib import Path

import jinja2
from flask import Flask, Response, redirect, render_template, request
from flask_babel import Babel, _
from werkzeug.middleware.proxy_fix import ProxyFix

import auth
import charts
import db
import jsonw
import language
import lastfm
import music
import packer
import scanner
import settings
from auth import AuthError, RequestTokenError
from charts import StatsPeriod
from music import Track
from routes import account as app_account
from routes import activity as app_activity
from routes import auth as app_auth
from routes import dislikes as app_dislikes
from routes import download as app_download
from routes import files as app_files
from routes import playlists as app_playlists
from routes import radio as app_radio
from routes import track as app_track
from routes import users as app_users

app = Flask(__name__, template_folder='templates')
app.register_blueprint(app_account.bp)
app.register_blueprint(app_activity.bp)
app.register_blueprint(app_auth.bp)
app.register_error_handler(AuthError, app_auth.handle_auth_error)
app.register_error_handler(RequestTokenError, app_auth.handle_token_error)
app.register_blueprint(app_dislikes.bp)
app.register_blueprint(app_download.bp)
app.register_blueprint(app_files.bp)
app.register_blueprint(app_playlists.bp)
app.register_blueprint(app_radio.bp)
app.register_blueprint(app_track.bp)
app.register_blueprint(app_users.bp)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=settings.proxies_x_forwarded_for)
app.jinja_env.undefined = jinja2.StrictUndefined
app.jinja_env.auto_reload = settings.dev
babel = Babel(app, locale_selector=language.get_locale)
log = logging.getLogger('app')
static_dir = Path('static')


@app.route('/')
def route_home():
    """
    Home page, with links to file manager and music player
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
    return render_template('home.jinja2',
                           user_is_admin=user.admin,
                           offline_mode=settings.offline_mode)


@app.route('/player')
def route_player():
    """
    Main player page. Serves player.jinja2 template file.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)

    return render_template('player.jinja2',
                           mobile=is_mobile(),
                           primary_playlist=user.primary_playlist,
                           offline_mode=settings.offline_mode)


@app.route('/static/js/player.js')
def route_player_js():
    """
    Concatenated javascript file for music player. Only used during development.
    """
    return Response(packer.pack(Path(static_dir, 'js', 'player')),
                    content_type='application/javascript')


@app.route('/info')
def route_info():
    """
    Information/manual page
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    return render_template('info.jinja2')


@app.route('/lastfm_callback')
def route_lastfm_callback():
    # After allowing access, last.fm sends the user to this page with an
    # authentication token. The authentication token can only be used once,
    # to obtain a session key. Session keys are stored in the database.

    # Cookies are not present here (because of cross-site redirect), so we
    # can't save the token just yet. Add another redirect step.

    auth_token = request.args['token']
    return render_template('lastfm_callback.jinja2',
                           auth_token=auth_token)


@app.route('/lastfm_connect', methods=['POST'])
def route_lastfm_connect():
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

@app.route('/lastfm_disconnect', methods=['POST'])
def route_lastfm_disconnect():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        conn.execute('DELETE FROM user_lastfm WHERE user=?',
                     (user.user_id,))
    return redirect('/account', code=303)


@app.route('/stats')
def route_stats():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

    return render_template('stats.jinja2')


@app.route('/stats_data')
def route_stats_data():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        period = StatsPeriod.from_str(request.args['period'])

    data = charts.get_data(period)
    return jsonw.json_response(data)


@app.route('/download_offline')
def route_download_offline():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        playlists = music.playlists(conn)

    return render_template('download_offline.jinja2',
                           playlists=playlists)


@app.route('/player_copy_track', methods=['POST'])
def route_player_copy_track():
    """
    Endpoint used by music player to copy a track to the user's primary playlist
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])
        playlist_name = request.json['playlist']

        playlist = music.user_playlist(conn, playlist_name, user.user_id)
        assert playlist.write or user.admin

        track = Track.by_relpath(conn, request.json['track'])

        if track.playlist == playlist.name:
            return Response(_('Track is already in this playlist'), content_type='text/plain')

        shutil.copy(track.path, playlist.path)

        scanner.scan_tracks(conn, playlist.name)

        return Response(None, 200)


@app.route('/install')
def route_install():
    return render_template('install.jinja2')


@app.route('/pwa')
def route_pwa():
    # Cannot have /player as an entrypoint directly, because for some reason the first request
    # to the start_url does not include cookies. Even a regular 302 redirect doesn't work!
    return '<meta http-equiv="refresh" content="0;URL=\'/player\'">'


@app.route('/health_check')
def route_health_check():
    return Response('ok', content_type='text/plain')


def is_mobile() -> bool:
    """
    Checks whether User-Agent looks like a mobile device (Android or iOS)
    """
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Android' in user_agent or 'iOS' in user_agent:
            return True
    return False


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    app.run(host='0.0.0.0', port=8080, debug=True)

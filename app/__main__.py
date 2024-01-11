"""
Main application file, containing all Flask routes
"""
import logging
from pathlib import Path

import jinja2
from flask import Flask, Response, abort, redirect, render_template, request
from flask_babel import Babel
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from app import (charts, db, jsonw, language, lastfm, logconfig, music, packer,
                 settings)
from app.auth import AuthError, RequestTokenError
from app.charts import StatsPeriod
from app.routes import account as app_account
from app.routes import activity as app_activity
from app.routes import auth as app_auth
from app.routes import dislikes as app_dislikes
from app.routes import download as app_download
from app.routes import files as app_files
from app.routes import news as app_news
from app.routes import player as app_player
from app.routes import playlists as app_playlists
from app.routes import radio as app_radio
from app.routes import track as app_track
from app.routes import users as app_users

from . import auth

app = Flask(__name__, template_folder='templates')
app.register_blueprint(app_account.bp)
app.register_blueprint(app_activity.bp)
app.register_blueprint(app_auth.bp)
app.register_error_handler(AuthError, app_auth.handle_auth_error)
app.register_error_handler(RequestTokenError, app_auth.handle_token_error)
app.register_blueprint(app_dislikes.bp)
app.register_blueprint(app_download.bp)
app.register_blueprint(app_files.bp)
app.register_blueprint(app_news.bp)
app.register_blueprint(app_player.bp)
app.register_blueprint(app_playlists.bp)
app.register_blueprint(app_radio.bp)
app.register_blueprint(app_track.bp)
app.register_blueprint(app_users.bp)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=settings.proxies_x_forwarded_for)
app.jinja_env.undefined = jinja2.StrictUndefined
app.jinja_env.auto_reload = settings.dev
babel = Babel(app, locale_selector=language.get_locale)
log = logging.getLogger('app')


@app.errorhandler(Exception)
def handle_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    log.exception('Unhandled exception')
    return Response('Sorry! Cannot continue due to unhandled exception. The error has been logged.', 500, content_type='text/plain')


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


@app.route('/static/js/player.js')
def route_player_js():
    """
    Concatenated javascript file for music player. Only used during development.
    """
    return Response(packer.pack(Path(settings.static_dir, 'js', 'player')),
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


@app.route('/install')
def route_install():
    return render_template('install.jinja2')


@app.route('/pwa')
def route_pwa():
    # Cannot have /player as an entrypoint directly, because for some reason the first request
    # to the start_url does not include cookies. Even a regular 302 redirect doesn't work!
    return '<meta http-equiv="refresh" content="0;URL=\'/player\'">'


@app.route('/csp_reports', methods=['POST'])
def route_csp_reports():
    # TODO Add rate limit
    assert request.content_type == 'application/csp-report'
    log.warning('Received Content-Security-Policy report: %s', jsonw.from_json(request.data))
    return Response(None, 200)


@app.route('/health_check')
def route_health_check():
    return Response('ok', content_type='text/plain')


if __name__ == '__main__':
    logconfig.apply()
    app.run(host='0.0.0.0', port=8080, debug=True)

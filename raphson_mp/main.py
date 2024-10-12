import logging

import jinja2

try:
    import prometheus_client
except ImportError:
    prometheus_client = None
from flask import Flask, Response
from flask_babel import Babel
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix

from raphson_mp import language
from raphson_mp.auth import AuthError
from raphson_mp.routes import account as app_account
from raphson_mp.routes import activity as app_activity
from raphson_mp.routes import auth as app_auth
from raphson_mp.routes import dislikes as app_dislikes
from raphson_mp.routes import download as app_download
from raphson_mp.routes import export as app_export
from raphson_mp.routes import files as app_files
from raphson_mp.routes import games as app_games
from raphson_mp.routes import news as app_news
from raphson_mp.routes import player as app_player
from raphson_mp.routes import playlist as app_playlist
from raphson_mp.routes import radio as app_radio
from raphson_mp.routes import root as app_root
from raphson_mp.routes import share as app_share
from raphson_mp.routes import stats as app_stats
from raphson_mp.routes import track as app_track
from raphson_mp.routes import users as app_users

log = logging.getLogger(__name__)


def _handle_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    log.exception('Unhandled exception')
    return Response('Sorry! Cannot continue due to an unhandled exception. The error has been logged. Please contact the server administrator.', 500, content_type='text/plain')


def get_app(proxy_count: int, template_reload: bool):
    app = Flask(__name__, template_folder='templates')
    app.register_error_handler(Exception, _handle_exception)
    app.register_error_handler(AuthError, app_auth.handle_auth_error)
    app.register_blueprint(app_account.bp)
    app.register_blueprint(app_activity.bp)
    app.register_blueprint(app_auth.bp)
    app.register_blueprint(app_dislikes.bp)
    app.register_blueprint(app_download.bp)
    app.register_blueprint(app_export.bp)
    app.register_blueprint(app_files.bp)
    app.register_blueprint(app_games.bp)
    app.register_blueprint(app_news.bp)
    app.register_blueprint(app_player.bp)
    app.register_blueprint(app_playlist.bp)
    app.register_blueprint(app_radio.bp)
    app.register_blueprint(app_root.bp)
    app.register_blueprint(app_share.bp)
    app.register_blueprint(app_stats.bp)
    app.register_blueprint(app_track.bp)
    app.register_blueprint(app_users.bp)
    if prometheus_client:
        from raphson_mp import prometheus  # pylint: disable=unused-import
        app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': prometheus_client.make_wsgi_app()})
    else:
        log.warning('prometheus_client is not available, continuing without /metrics endpoint')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count)
    app.jinja_env.auto_reload = template_reload
    app.jinja_env.undefined = jinja2.StrictUndefined
    app.jinja_env.autoescape = True  # autoescape is on by default, but only for files extensions like .html, but we use .jinja2. Enable autoescape unconditionally.
    Babel(app, locale_selector=language.get_locale)
    return app

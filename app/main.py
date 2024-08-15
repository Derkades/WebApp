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

from app import language
from app.auth import AuthError, RequestTokenError
from app.routes import account as app_account
from app.routes import activity as app_activity
from app.routes import auth as app_auth
from app.routes import dislikes as app_dislikes
from app.routes import download as app_download
from app.routes import files as app_files
from app.routes import games as app_games
from app.routes import news as app_news
from app.routes import player as app_player
from app.routes import playlists as app_playlists
from app.routes import radio as app_radio
from app.routes import root as app_root
from app.routes import share as app_share
from app.routes import stats as app_stats
from app.routes import track as app_track
from app.routes import users as app_users

log = logging.getLogger('app.main')


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
    app.register_error_handler(RequestTokenError, app_auth.handle_token_error)
    app.register_blueprint(app_account.bp)
    app.register_blueprint(app_activity.bp)
    app.register_blueprint(app_auth.bp)
    app.register_blueprint(app_dislikes.bp)
    app.register_blueprint(app_download.bp)
    app.register_blueprint(app_files.bp)
    app.register_blueprint(app_games.bp)
    app.register_blueprint(app_news.bp)
    app.register_blueprint(app_player.bp)
    app.register_blueprint(app_playlists.bp)
    app.register_blueprint(app_radio.bp)
    app.register_blueprint(app_root.bp)
    app.register_blueprint(app_share.bp)
    app.register_blueprint(app_stats.bp)
    app.register_blueprint(app_track.bp)
    app.register_blueprint(app_users.bp)
    if prometheus_client:
        from app import prometheus  # pylint: disable=unused-import
        app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': prometheus_client.make_wsgi_app()})
    else:
        log.warning('prometheus_client is not available, continuing without /metrics endpoint')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count)
    app.jinja_env.auto_reload = template_reload
    app.jinja_env.undefined = jinja2.StrictUndefined
    Babel(app, locale_selector=language.get_locale)
    return app

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

from raphson_mp import language, settings

log = logging.getLogger(__name__)


def _handle_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    log.exception('Unhandled exception')
    return Response('Sorry! Cannot continue due to an unhandled exception. The error has been logged. Please contact the server administrator.', 500, content_type='text/plain')


def get_app(proxy_count: int, template_reload: bool) -> Flask:
    app = Flask(__name__, template_folder='templates')
    app.register_error_handler(Exception, _handle_exception)

    from raphson_mp.routes import auth, games, player, playlist, root, tracks
    app.register_error_handler(auth.AuthError, auth.handle_auth_error)
    app.register_blueprint(auth.bp)
    app.register_blueprint(games.bp)
    app.register_blueprint(player.bp)
    app.register_blueprint(playlist.bp)
    app.register_blueprint(root.bp)
    app.register_blueprint(tracks.bp)

    if settings.offline_mode:
        from raphson_mp.routes import activity_offline, track_offline
        app.register_blueprint(activity_offline.bp)
        app.register_blueprint(track_offline.bp)
    else:
        from raphson_mp.routes import (account, activity, dislikes, download,
                                       export, files, news, radio, share,
                                       stats, track, users)
        app.register_blueprint(account.bp)
        app.register_blueprint(activity.bp)
        app.register_blueprint(dislikes.bp)
        app.register_blueprint(download.bp)
        app.register_blueprint(export.bp)
        app.register_blueprint(files.bp)
        app.register_blueprint(news.bp)
        app.register_blueprint(radio.bp)
        app.register_blueprint(share.bp)
        app.register_blueprint(stats.bp)
        app.register_blueprint(track.bp)
        app.register_blueprint(users.bp)

    if prometheus_client:
        from raphson_mp import prometheus
        prometheus.register_collectors()
        app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {'/metrics': prometheus_client.make_wsgi_app()})
    else:
        log.warning('prometheus_client is not available, continuing without /metrics endpoint')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count)
    app.jinja_env.auto_reload = template_reload
    app.jinja_env.undefined = jinja2.StrictUndefined
    app.jinja_env.autoescape = True  # autoescape is on by default, but only for files extensions like .html, but we use .jinja2. Enable autoescape unconditionally.
    Babel(app, locale_selector=language.get_locale)
    return app

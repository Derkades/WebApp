import shutil
from sqlite3 import Connection
import time
from typing import cast

from flask import Blueprint, Response, abort, redirect, render_template, request
from flask_babel import _

from raphson_mp import db, music, scanner, settings, util
from raphson_mp.auth import StandardUser, User
from raphson_mp.decorators import route
from raphson_mp.music import Track

bp = Blueprint('player', __name__, url_prefix='/player')


@route(bp, '', redirect_to_login=True)
def route_player(_conn: Connection, user: User):
    """
    Main player page. Serves player.jinja2 template file.
    """
    response = Response(render_template('player.jinja2',
                           mobile=util.is_mobile(),
                           primary_playlist=user.primary_playlist,
                           load_timestamp=int(time.time()),
                           offline_mode=settings.offline_mode))

    # Refresh token cookie
    if isinstance(user, StandardUser):
        user.session.set_cookie(response)

    return response


@route(bp, '/copy_track', methods=['POST'], write=True)
def route_copy_track(conn: Connection, user: User):
    """
    Endpoint used by music player to copy a track to the user's primary playlist
    """
    playlist_name = cast(str, request.json['playlist'])

    playlist = music.user_playlist(conn, playlist_name, user.user_id)
    if not user.admin and not playlist.write:
        abort(403)

    track = Track.by_relpath(conn, cast(str, request.json['track']))

    if track is None:
        abort(400, 'track does not exist')

    if track.playlist == playlist.name:
        abort(400, 'track already in playlist')

    shutil.copy(track.path, playlist.path)

    # TODO use scanner.scan_track to only scan the newly added track
    scanner.scan_tracks(conn, playlist.name)

    return Response(None, 200)

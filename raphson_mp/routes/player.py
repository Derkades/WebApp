import shutil
import time

from flask import Blueprint, Response, render_template, request
from flask_babel import _

from raphson_mp import auth, db, music, scanner, settings, util
from raphson_mp.music import Track

bp = Blueprint('player', __name__, url_prefix='/player')


@bp.route('')
def route_player():
    """
    Main player page. Serves player.jinja2 template file.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        csrf_token = user.get_csrf()

    return render_template('player.jinja2',
                           mobile=util.is_mobile(),
                           primary_playlist=user.primary_playlist,
                           load_timestamp=int(time.time()),
                           offline_mode=settings.offline_mode,
                           csrf_token=csrf_token)


@bp.route('/copy_track', methods=['POST'])
def route_copy_track():
    """
    Endpoint used by music player to copy a track to the user's primary playlist
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        playlist_name = request.json['playlist']

        playlist = music.user_playlist(conn, playlist_name, user.user_id)
        assert playlist.write or user.admin

        track = Track.by_relpath(conn, request.json['track'])

        if track.playlist == playlist.name:
            return Response(_('Track is already in this playlist'), content_type='text/plain')

        shutil.copy(track.path, playlist.path)

        # TODO use scanner.scan_track to only scan the newly added track
        scanner.scan_tracks(conn, playlist.name)

        return Response(None, 200)

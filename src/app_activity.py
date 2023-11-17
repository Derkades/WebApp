
import time
from sqlite3 import Connection

from flask import Blueprint, render_template
from flask_babel import _, format_timedelta

import auth
import db
from music import Track

bp = Blueprint('activity', __name__, url_prefix='/activity')


def get_file_changes_list(conn: Connection, limit: int) -> list[dict[str, str]]:
    result = conn.execute(f'''
                              SELECT timestamp, action, playlist, track
                              FROM scanner_log
                              ORDER BY id DESC
                              LIMIT {limit}
                              ''')

    action_trans = {
        'insert': _('Added'),
        'delete': _('Removed'),
        'update': _('Modified'),
    }

    return [{'timestamp': timestamp,
             'time_ago': format_timedelta(timestamp - int(time.time()), add_direction=True),
             'action': action_trans[action],
             'playlist': playlist,
             'track': track}
             for timestamp, action, playlist, track in result]


@bp.route('/files')
def route_files():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        changes = get_file_changes_list(conn, 2000)

    return render_template('activity_files.jinja2',
                           changes=changes)


@bp.route('/')
def route_activity():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

    return render_template('activity.jinja2')


@bp.route('/data')
def route_data():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        result = conn.execute('''
                              SELECT user.username, user.nickname, track.playlist, track, paused, progress
                              FROM now_playing
                                JOIN user ON now_playing.user = user.id
                                JOIN track ON now_playing.track = track.path
                              WHERE now_playing.timestamp > ?
                              ''',
                              (int(time.time()) - 20,))  # based on JS update interval

        now_playing = []
        for username, nickname, playlist_name, relpath, paused, progress in result:
            track = Track.by_relpath(conn, relpath)
            meta = track.metadata()
            now_playing.append({'path': relpath,
                             'username': nickname if nickname else username,
                             'playlist': playlist_name,
                             'title': meta.title,
                             'artists': meta.artists,
                             'fallback_title': meta.display_title(),
                             'paused': paused,
                             'progress': progress})

        result = conn.execute('''
                              SELECT history.timestamp, user.username, user.nickname, history.playlist, history.track
                              FROM history
                                  LEFT JOIN user ON history.user = user.id
                              WHERE history.private = 0
                              ORDER BY history.id DESC
                              LIMIT 10
                              ''')
        history = []
        for timestamp, username, nickname, playlist, relpath in result:
            time_ago = format_timedelta(timestamp - int(time.time()), add_direction=True)
            track = Track.by_relpath(conn, relpath)
            if track:
                meta = track.metadata()
                title = meta.display_title()
            else:
                title = relpath

            history.append({'time_ago': time_ago,
                            'username': nickname if nickname else username,
                            'playlist': playlist,
                            'title': title})

        file_changes = get_file_changes_list(conn, 10)

    return {'now_playing': now_playing,
            'history': history,
            'file_changes': file_changes}


@bp.route('/all')
def route_all():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        result = conn.execute('''
                              SELECT history.timestamp, user.username, user.nickname, history.playlist, history.track, track.path IS NOT NULL
                              FROM history
                                  LEFT JOIN user ON history.user = user.id
                                  LEFT JOIN track ON history.track = track.path
                              ORDER BY history.id DESC
                              LIMIT 1000
                              ''')
        history = []
        for timestamp, username, nickname, playlist, relpath, track_exists in result:
            if track_exists:
                track = Track.by_relpath(conn, relpath)
                meta = track.metadata()
                title = meta.display_title()
            else:
                title = relpath

            history.append({'time': timestamp,
                            'username': nickname if nickname else username,
                            'playlist': playlist,
                            'title': title})

    return render_template('activity_all.jinja2',
                           history=history)

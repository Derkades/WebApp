
import logging
from threading import Thread
import time
from sqlite3 import Connection
from typing import Any, cast

from flask import Blueprint, Response, abort, render_template, request
from flask_babel import _, format_timedelta

from raphson_mp import auth, db
from raphson_mp.auth import PrivacyOption, StandardUser, User
from raphson_mp.decorators import route
from raphson_mp.music import Track

log = logging.getLogger(__name__)
bp = Blueprint('activity', __name__, url_prefix='/activity')


def get_file_changes_list(conn: Connection, limit: int) -> list[dict[str, str]]:
    """
    Helper function to get a list of file changes as a dictionary list. Used by route_data to
    provide a JSON API and by route_all to provide a static page with more history.
    """
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


@route(bp, '', redirect_to_login=True)
def route_activity(conn: Connection, user: User):
    """
    Main activity page, showing currently playing tracks and history of
    played tracks and modified files.
    """
    return render_template('activity.jinja2')


@route(bp, '/data')
def route_data(conn: Connection, user: User):
    """
    Endpoint providing data for main activity page in JSON format.
    """
    result = conn.execute('''
                            SELECT user.username, user.nickname, timestamp, track, paused, position
                            FROM now_playing
                            JOIN user ON now_playing.user = user.id
                            INNER JOIN track ON now_playing.track = track.path
                            WHERE now_playing.timestamp > ?
                            ORDER BY player_id
                            ''',
                            (int(time.time()) - 70,))  # based on JS update interval

    now_playing: list[dict[str, str|int|list[str]|None]] = []

    current_timestamp = int(time.time())
    for username, nickname, timestamp, relpath, paused, position in result:
        track = cast(Track, Track.by_relpath(conn, relpath))
        meta = track.metadata()
        if not paused:
            corrected_position = position + current_timestamp - timestamp
            if corrected_position < meta.duration:
                position = corrected_position
        now_playing.append({'username': nickname if nickname else username,
                            'timestamp': timestamp,
                            'paused': paused,
                            'position': position,
                            **track.info_dict()})

    result = conn.execute('''
                            SELECT history.timestamp, user.username, user.nickname, history.track
                            FROM history
                                LEFT JOIN user ON history.user = user.id
                                INNER JOIN track ON history.track = track.path -- To ensure no deleted tracks are returned
                            WHERE history.private = 0
                            ORDER BY history.timestamp DESC
                            LIMIT 10
                            ''')

    history = [{'time_ago': format_timedelta(timestamp - int(time.time()), add_direction=True),
                'username': nickname if nickname else username,
                **cast(Track, Track.by_relpath(conn, relpath)).info_dict()}
                for timestamp, username, nickname, relpath in result]

    file_changes = get_file_changes_list(conn, 10)

    return {'now_playing': now_playing,
            'history': history,
            'file_changes': file_changes}


@route(bp, '/files')
def route_files(conn: Connection, user: User):
    """
    Page with long static list of changed files history, similar to route_all()
    """
    changes = get_file_changes_list(conn, 2000)

    return render_template('activity_files.jinja2',
                           changes=changes)


@route(bp, '/all')
def route_all(conn: Connection, user: User):
    """
    Page with long static list of playback history, similar to route_files()
    """
    result = conn.execute('''
                            SELECT history.timestamp, user.username, user.nickname, history.playlist, history.track, track.path IS NOT NULL
                            FROM history
                                LEFT JOIN user ON history.user = user.id
                                LEFT JOIN track ON history.track = track.path
                            ORDER BY history.timestamp DESC
                            LIMIT 5000
                            ''')
    history: list[dict[str, Any]] = []
    for timestamp, username, nickname, playlist, relpath, track_exists in result:
        if track_exists:
            title = cast(Track, Track.by_relpath(conn, relpath)).metadata().display_title()
        else:
            title = relpath

        history.append({'time': timestamp,
                        'username': nickname if nickname else username,
                        'playlist': playlist,
                        'title': title})

    return render_template('activity_all.jinja2',
                           history=history)


@route(bp, '/now_playing', methods=['POST'], write=True)
def route_now_playing(conn: Connection, user: StandardUser):
    """
    Send info about currently playing track. Sent frequently by the music player.
    POST body should contain a json object with:
     - csrf (str): CSRF token
     - track (str): Track relpath
     - paused (bool): Whether track is paused
     - progress (int): Track position, as a percentage
    """
    from raphson_mp import lastfm

    if user.privacy != PrivacyOption.NONE:
        log.info('Ignoring, user has enabled private mode')
        return Response('ok', 200, content_type='text/plain')

    player_id = cast(str, request.json['player_id'])
    relpath = cast(str, request.json['track'])
    paused = cast(bool, request.json['paused'])

    track = Track.by_relpath(conn, relpath)

    if track is None:
        abort(400, 'track does not exist')

    if 'progress' in request.json:
        log.warning('now_playing received with legacy progress data')
        meta = track.metadata()
        position = int(cast(int, request.json['progress']) / 100 * meta.duration)
    else:
        position = cast(int, request.json['position'])

    lastfm_update_timestamp = conn.execute('''
                    INSERT INTO now_playing (player_id, user, timestamp, track, paused, position)
                    VALUES (:player_id, :user_id, :timestamp, :relpath, :paused, :position)
                    ON CONFLICT(player_id) DO UPDATE
                        SET timestamp=:timestamp, track=:relpath, paused=:paused, position=:position
                    RETURNING lastfm_update_timestamp
                    ''',
                    {'player_id': player_id,
                    'user_id': user.user_id,
                    'timestamp': int(time.time()),
                    'relpath': relpath,
                    'paused': paused,
                    'position': position}).fetchone()[0]

    user_key = lastfm.get_user_key(user)
    if user_key and not paused and time.time() - lastfm_update_timestamp > 60:
        meta = track.metadata()
        conn.execute('UPDATE now_playing SET lastfm_update_timestamp = unixepoch() WHERE player_id = ?', (player_id,))

        def update_lastfm():
            log.info('Sending now playing to last.fm: %s', track.relpath)
            lastfm.update_now_playing(user_key, meta)

        Thread(target=update_lastfm).start()

    return Response(None, 200, content_type='text/plain')


@route(bp, '/played', methods=['POST'], write=True)
def route_played(conn: Connection, user: StandardUser):
    """
    Route to submit an entry to played tracks history, optionally also
    scrobbling to last.fm. Used by web music player and also by offline
    sync to submit many previously played tracks.
    POST body:
     - track: relpath
     - timestamp: time at which track met played conditions (roughly)
     - csrf: csrf token (ignored in offline mode)
    """
    from raphson_mp import lastfm

    track = Track.by_relpath(conn, cast(str, request.json['track']))
    if track is None:
        log.warning('skipping track that does not exist: %s', cast(str, request.json['track']))
        return Response('ok', 200, content_type='text/plain')

    timestamp = int(cast(str, request.json['timestamp']))

    # In offline mode, tracks are chosen without last_chosen being updated. Update it now.
    conn.execute('UPDATE track SET last_chosen=MAX(last_chosen, ?) WHERE path=?',
                    (timestamp, track.relpath))

    if user.privacy == PrivacyOption.HIDDEN:
        log.info('Ignoring because privacy==hidden')
        return Response('ok', 200)

    private = user.privacy == PrivacyOption.AGGREGATE

    conn.execute('''
                    INSERT INTO history (timestamp, user, track, playlist, private)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (timestamp, user.user_id, track.relpath, track.playlist, private))

    # last.fm requires track length to be at least 30 seconds
    if private or track.metadata().duration < 30:
        # No need to scrobble, nothing more to do
        return Response('ok', 200, content_type='text/plain')

    lastfm_key = lastfm.get_user_key(user)

    if lastfm_key:
        meta = track.metadata()

        def scrobble():
            log.info('Scrobbling to last.fm: %s', track.relpath)
            lastfm.scrobble(lastfm_key, meta, timestamp)

        Thread(target=scrobble).start()

    return Response('ok', 200, content_type='text/plain')

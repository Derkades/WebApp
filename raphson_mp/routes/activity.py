
import logging
import time
from sqlite3 import Connection

from flask import Blueprint, Response, render_template, request
from flask_babel import _, format_timedelta

from raphson_mp import auth, db, settings
from raphson_mp.auth import PrivacyOption
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


@bp.route('')
def route_activity():
    """
    Main activity page, showing currently playing tracks and history of
    played tracks and modified files.
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn, redirect_to_login=True)

    return render_template('activity.jinja2')


@bp.route('/data')
def route_data():
    """
    Endpoint providing data for main activity page in JSON format.
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        result = conn.execute('''
                              SELECT user.username, user.nickname, track, paused, progress
                              FROM now_playing
                                JOIN user ON now_playing.user = user.id
                                INNER JOIN track ON now_playing.track = track.path
                              WHERE now_playing.timestamp > ?
                              ORDER BY player_id
                              ''',
                              (int(time.time()) - 70,))  # based on JS update interval

        now_playing = [{'username': nickname if nickname else username,
                        'paused': paused,
                        'progress': progress,
                        **Track.by_relpath(conn, relpath).info_dict()}
                       for username, nickname, relpath, paused, progress in result]

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
                    **Track.by_relpath(conn, relpath).info_dict()}
                   for timestamp, username, nickname, relpath in result]

        file_changes = get_file_changes_list(conn, 10)

    return {'now_playing': now_playing,
            'history': history,
            'file_changes': file_changes}


@bp.route('/files')
def route_files():
    """
    Page with long static list of changed files history, similar to route_all()
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn, redirect_to_login=True)
        changes = get_file_changes_list(conn, 2000)

    return render_template('activity_files.jinja2',
                           changes=changes)


@bp.route('/all')
def route_all():
    """
    Page with long static list of playback history, similar to route_files()
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn, redirect_to_login=True)

        result = conn.execute('''
                              SELECT history.timestamp, user.username, user.nickname, history.playlist, history.track, track.path IS NOT NULL
                              FROM history
                                  LEFT JOIN user ON history.user = user.id
                                  LEFT JOIN track ON history.track = track.path
                              ORDER BY history.timestamp DESC
                              LIMIT 5000
                              ''')
        history = []
        for timestamp, username, nickname, playlist, relpath, track_exists in result:
            if track_exists:
                title = Track.by_relpath(conn, relpath).metadata().display_title()
            else:
                title = relpath

            history.append({'time': timestamp,
                            'username': nickname if nickname else username,
                            'playlist': playlist,
                            'title': title})

    return render_template('activity_all.jinja2',
                           history=history)


@bp.route('/now_playing', methods=['POST'])
def route_now_playing():
    """
    Send info about currently playing track. Sent frequently by the music player.
    POST body should contain a json object with:
     - csrf (str): CSRF token
     - track (str): Track relpath
     - paused (bool): Whether track is paused
     - progress (int): Track position, as a percentage
    """
    from raphson_mp import lastfm

    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        if user.privacy != PrivacyOption.NONE:
            log.info('Ignoring, user has enabled private mode')
            return Response('ok', 200, content_type='text/plain')

        player_id = request.json['player_id']
        assert isinstance(player_id, str)
        relpath = request.json['track']
        assert isinstance(relpath, str)
        paused = request.json['paused']
        assert isinstance(paused, bool)
        progress = request.json['progress']
        assert isinstance(progress, int)

        conn.execute('''
                     INSERT INTO now_playing (player_id, user, timestamp, track, paused, progress)
                     VALUES (:player_id, :user_id, :timestamp, :relpath, :paused, :progress)
                     ON CONFLICT(player_id) DO UPDATE
                         SET timestamp=:timestamp, track=:relpath, paused=:paused, progress=:progress
                     ''',
                     {'player_id': player_id,
                      'user_id': user.user_id,
                      'timestamp': int(time.time()),
                      'relpath': relpath,
                      'paused': paused,
                      'progress': progress})

        user_key = lastfm.get_user_key(user)
        if user_key and not paused:
            track = Track.by_relpath(conn, relpath)
            meta = track.metadata()

    # Don't keep database connection open while making last.fm request
    if user_key and not paused:
        log.info('Sending now playing to last.fm: %s', track.relpath)
        lastfm.update_now_playing(user_key, meta)

    return Response(None, 200, content_type='text/plain')


@bp.route('/played', methods=['POST'])
def route_played():
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

    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        track = Track.by_relpath(conn, request.json['track'])
        if track is None:
            log.warning('skipping track that does not exist: %s', request.json['track'])
            return Response('ok', 200, content_type='text/plain')

        timestamp = int(request.json['timestamp'])

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

        if not lastfm_key:
            # User has not linked their account, no need to scrobble
            return Response('ok', 200, content_type='text/plain')

        meta = track.metadata()

    # Scrobble request takes a while, so close database connection first
    log.info('Scrobbling to last.fm: %s', track.relpath)
    lastfm.scrobble(lastfm_key, meta, timestamp)

    return Response('ok', 200, content_type='text/plain')

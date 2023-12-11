
import logging
import time
from sqlite3 import Connection

from flask import Blueprint, Response, render_template, request
from flask_babel import _, format_timedelta

from app import auth, db, lastfm, settings
from app.auth import PrivacyOption
from app.music import Track

log = logging.getLogger('app.routes.activity')
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
        auth.verify_auth_cookie(conn, redirect_to_login=True)
        changes = get_file_changes_list(conn, 2000)

    return render_template('activity_files.jinja2',
                           changes=changes)


@bp.route('')
def route_activity():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn, redirect_to_login=True)

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
        auth.verify_auth_cookie(conn, redirect_to_login=True)

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
    if settings.offline_mode:
        log.info('Ignoring now playing in offline mode')
        return Response(None, 200)

    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

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

        user_key = lastfm.get_user_key(user)

        if user_key:
            result = conn.execute('''
                                  SELECT timestamp FROM now_playing
                                  WHERE user = ? AND track = ?
                                  ''', (user.user_id, relpath)).fetchone()
            previous_update = None if result is None else result[0]

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

        if not user_key:
            # Skip last.fm now playing, account is not linked
            return Response(None, 200, content_type='text/plain')

        # If now playing has already been sent for this track, only send an update to
        # last.fm if it was more than 5 minutes ago.
        if previous_update is not None and int(time.time()) - previous_update < 5*60:
            # Skip last.fm now playing, already sent recently
            return Response(None, 200, content_type='text/plain')

        track = Track.by_relpath(conn, relpath)
        meta = track.metadata()

    # Request to last.fm takes a while, so close database connection first

    log.info('Sending now playing to last.fm: %s', track.relpath)
    lastfm.update_now_playing(user_key, meta)
    return Response(None, 200, content_type='text/plain')


@bp.route('/played', methods=['POST'])
def route_played():
    if settings.offline_mode:
        with db.offline() as conn:
            track = request.json['track']
            timestamp = request.json['timestamp']
            conn.execute('INSERT INTO history VALUES (?, ?)',
                         (timestamp, track))
        return Response(None, 200)

    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        track = request.json['track']
        timestamp = int(request.json['timestamp'])

        # In offline mode, tracks are chosen without last_chosen being updated. Update it now.
        conn.execute('UPDATE track SET last_chosen=MAX(last_chosen, ?) WHERE path=?',
                     (timestamp, track))

        if user.privacy == PrivacyOption.HIDDEN:
            log.info('Ignoring because privacy==hidden')
            return Response('ok', 200)

        playlist = track[:track.index('/')]
        private = user.privacy == PrivacyOption.AGGREGATE

        conn.execute('''
                     INSERT INTO history (timestamp, user, track, playlist, private)
                     VALUES (?, ?, ?, ?, ?)
                     ''',
                     (timestamp, user.user_id, track, playlist, private))

        if private or not request.json['lastfmEligible']:
            # No need to scrobble, nothing more to do
            return Response('ok', 200, content_type='text/plain')

        lastfm_key = lastfm.get_user_key(user)

        if not lastfm_key:
            # User has not linked their account, no need to scrobble
            return Response('ok', 200, content_type='text/plain')

        track = Track.by_relpath(conn, request.json['track'])
        meta = track.metadata()
        if meta is None:
            log.warning('Track is missing from database. Probably deleted by a rescan after the track was queued.')
            return Response('ok', 200, content_type='text/plain')

    # Scrobble request takes a while, so close database connection first
    log.info('Scrobbling to last.fm: %s', track.relpath)
    lastfm.scrobble(lastfm_key, meta, timestamp)

    return Response('ok', 200, content_type='text/plain')

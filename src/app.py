"""
Main application file, containing all Flask routes
"""
import logging
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jinja2
from flask import Flask, Response, abort, redirect, render_template, request
from flask_babel import Babel, _
from werkzeug.middleware.proxy_fix import ProxyFix

import app_account
import app_activity
import app_auth
import app_download
import app_files
import app_playlists
import app_radio
import app_users
import auth
import charts
import db
import downloader
import genius
import jsonw
import language
import lastfm
import metadata
import music
import packer
import scanner
import settings
from auth import AuthError, PrivacyOption, RequestTokenError
from charts import StatsPeriod
from image import ImageFormat, ImageQuality
from music import AudioType, Track

app = Flask(__name__, template_folder='templates')
app.register_blueprint(app_account.bp)
app.register_blueprint(app_activity.bp)
app.register_blueprint(app_auth.bp)
app.register_error_handler(AuthError, app_auth.handle_auth_error)
app.register_error_handler(RequestTokenError, app_auth.handle_token_error)
app.register_blueprint(app_download.bp)
app.register_blueprint(app_files.bp)
app.register_blueprint(app_playlists.bp)
app.register_blueprint(app_radio.bp)
app.register_blueprint(app_users.bp)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=settings.proxies_x_forwarded_for)
app.jinja_env.undefined = jinja2.StrictUndefined
app.jinja_env.auto_reload = settings.dev
babel = Babel(app, locale_selector=language.get_locale)
log = logging.getLogger('app')
static_dir = Path('static')


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


@app.route('/player')
def route_player():
    """
    Main player page. Serves player.jinja2 template file.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        row = conn.execute('SELECT primary_playlist FROM user WHERE id=?',
                           (user.user_id,)).fetchone()
        primary_playlist = row[0] if row else None

    return render_template('player.jinja2',
                           mobile=is_mobile(),
                           primary_playlist=primary_playlist,
                           offline_mode=settings.offline_mode)


@app.route('/static/js/player.js')
def route_player_js():
    """
    Concatenated javascript file for music player. Only used during development.
    """
    return Response(packer.pack(Path(static_dir, 'js', 'player')),
                    content_type='application/javascript')


@app.route('/info')
def route_info():
    """
    Information/manual page
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    return render_template('info.jinja2')


@app.route('/choose_track', methods=['GET'])
def route_choose_track():
    """
    Choose random track from the provided playlist directory.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.args['csrf'])

        dir_name = request.args['playlist_dir']
        playlist = music.playlist(conn, dir_name)
        if 'tag_mode' in request.args:
            tag_mode = request.args['tag_mode']
            assert tag_mode in {'allow', 'deny'}
            tags = request.args['tags'].split(';')
            chosen_track = playlist.choose_track(user, tag_mode=tag_mode, tags=tags)
        else:
            chosen_track = playlist.choose_track(user)

    return {'path': chosen_track.relpath}


@app.route('/get_track')
def route_get_track():
    """
    Get transcoded audio for the given track path.
    """
    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            path = request.args['path']
            music_data, = conn.execute('SELECT music_data FROM content WHERE path=?',
                                       (path,))
            return Response(music_data, content_type='audio/webm')

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])

    if track is None:
        return abort(404, 'Track does not exist')

    parsed_mtime = datetime.fromtimestamp(track.mtime, timezone.utc)
    if request.if_modified_since and parsed_mtime <= request.if_modified_since:
        return Response(None, 304)

    type_str = request.args['type']
    if type_str == 'webm_opus_high':
        audio_type = AudioType.WEBM_OPUS_HIGH
        media_type = 'audio/webm'
    elif type_str == 'webm_opus_low':
        audio_type = AudioType.WEBM_OPUS_LOW
        media_type = 'audio_webm'
    elif type_str == 'mp4_aac':
        audio_type = AudioType.MP4_AAC
        media_type = 'audio/mp4'
    elif type_str == 'mp3_with_metadata':
        audio_type = AudioType.MP3_WITH_METADATA
        media_type = 'audio/mp3'
    else:
        raise ValueError(type_str)

    audio = track.transcoded_audio(audio_type)
    response = Response(audio, content_type=media_type)
    response.last_modified = parsed_mtime
    response.cache_control.no_cache = True  # always revalidate cache
    response.accept_ranges = 'bytes'  # Workaround for Chromium bug https://stackoverflow.com/a/65804889
    if audio_type == AudioType.MP3_WITH_METADATA:
        mp3_name = re.sub(r'[^\x00-\x7f]',r'', track.metadata().display_title())
        response.headers['Content-Disposition'] = f'attachment; filename="{mp3_name}"'
    return response


@app.route('/get_album_cover')
def route_get_album_cover() -> Response:
    """
    Get album cover image for the provided track path.
    """
    # TODO Album title and album artist as parameters, instead of track path

    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            path = request.args['path']
            cover_data, = conn.execute('SELECT cover_data FROM content WHERE path=?',
                                       (path,))
            return Response(cover_data, content_type='image/webp')

    meme = 'meme' in request.args and bool(int(request.args['meme']))

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])

        quality_str = request.args['quality']
        if quality_str == 'high':
            quality = ImageQuality.HIGH
        elif quality_str == 'low':
            quality = ImageQuality.LOW
        elif quality_str == 'tiny':
            quality = ImageQuality.TINY
        else:
            raise ValueError('invalid quality')

        image_bytes = track.get_cover_thumbnail(meme, ImageFormat.WEBP, quality)

    return Response(image_bytes, content_type='image/webp')


@app.route('/get_lyrics')
def route_get_lyrics():
    """
    Get lyrics for the provided track path.
    """
    if settings.offline_mode:
        with db.offline(read_only=True) as conn:
            path = request.args['path']
            lyrics_json, = conn.execute('SELECT lyrics_json FROM content WHERE path=?',
                                        (path,))
            return Response(lyrics_json, content_type='application/json')

    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        track = Track.by_relpath(conn, request.args['path'])
        meta = track.metadata()

    lyrics = genius.get_lyrics(meta.lyrics_search_query())
    if lyrics is None:
        return {'found': False}

    return {
        'found': True,
        'source': lyrics.source_url,
        'html': lyrics.lyrics_html,
    }


@app.route('/ytdl', methods=['POST'])
def route_ytdl():
    """
    Use yt-dlp to download the provided URL to a playlist directory
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        directory = request.json['directory']
        url = request.json['url']

        playlist = music.playlist(conn, directory)
        if not playlist.has_write_permission(user):
            return abort(403, 'No write permission for this playlist')

        log.info('ytdl %s %s', directory, url)

    # Release database connection during download

    def generate():
        status_code = yield from downloader.download(playlist.path, url)
        if status_code == 0:
            yield 'Scanning playlists...\n'
            with db.connect() as conn:
                playlist2 = music.playlist(conn, directory)
                scanner.scan_tracks(conn, playlist2.name)
            yield 'Done!'
        else:
            yield f'Failed with status code {status_code}'

    return Response(generate(), content_type='text/plain')


@app.route('/track_list')
def route_track_list():
    """
    Return list of playlists and tracks.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)

        timestamp_row = conn.execute('''
                                     SELECT timestamp FROM scanner_log
                                     ORDER BY id DESC
                                     LIMIT 1
                                     ''').fetchone()
        if timestamp_row:
            last_modified = datetime.fromtimestamp(timestamp_row[0], timezone.utc)
        else:
            last_modified = datetime.now(timezone.utc)

        if request.if_modified_since and last_modified <= request.if_modified_since:
            log.info('Last modified before If-Modified-Since header')
            return Response(None, 304)  # Not Modified

        user_playlists = music.user_playlists(conn, user.user_id, all_writable=user.admin)

        playlist_response: list[dict[str, Any]] = []

        for playlist in user_playlists:
            if playlist.track_count == 0:
                continue

            playlist_json = {
                'name': playlist.name,
                'favorite': playlist.favorite,
                'write': playlist.write,
                'tracks': [],
            }
            playlist_response.append(playlist_json)

            track_rows = conn.execute('''
                                      SELECT path, mtime, duration, title, album, album_artist, year
                                      FROM track
                                      WHERE playlist=?
                                      ''', (playlist.name,)).fetchall()

            for relpath, mtime, duration, title, album, album_artist, year in track_rows:
                track_json = {
                    'path': relpath,
                    'mtime': mtime,
                    'duration': duration,
                    'title': title,
                    'album': album,
                    'album_artist': album_artist,
                    'year': year,
                    'artists': None,
                    'tags': [],
                }
                playlist_json['tracks'].append(track_json)

                artist_rows = conn.execute('SELECT artist FROM track_artist WHERE track=?', (relpath,)).fetchall()
                if artist_rows:
                    track_json['artists'] = music.sort_artists([row[0] for row in artist_rows], album_artist)

                tag_rows = conn.execute('SELECT tag FROM track_tag WHERE track=?', (relpath,))
                track_json['tags'] = [tag for tag, in tag_rows]

    return jsonw.json_response({'playlists': playlist_response}, last_modified=last_modified)


@app.route('/update_metadata', methods=['POST'])
def route_update_metadata():
    """
    Endpoint to update track metadata
    """
    payload = request.json
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(payload['csrf'])

        track = Track.by_relpath(conn, payload['path'])
        assert track is not None

        playlist = music.playlist(conn, track.playlist)
        if not playlist.has_write_permission(user):
            return Response('No write permission for this playlist', 403, content_type='text/plain')

        track.write_metadata(title=payload['metadata']['title'],
                             album=payload['metadata']['album'],
                             artist='; '.join(payload['metadata']['artists']),
                             album_artist=payload['metadata']['album_artist'],
                             genre='; '.join(payload['metadata']['tags']),
                             date=payload['metadata']['year'])

    return Response(None, 200)


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
    return redirect('/account')


@app.route('/now_playing', methods=['POST'])
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


@app.route('/history_played', methods=['POST'])
def route_history_played():
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

        if user.privacy == PrivacyOption.HIDDEN:
            log.info('Ignoring because privacy==hidden')
            return Response('ok', 200)

        track = request.json['track']
        playlist = track[:track.index('/')]
        timestamp = request.json['timestamp']
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


@app.route('/dislikes_add', methods=['POST'])
def route_add_dislikes_add():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])
        track = request.json['track']
        conn.execute('INSERT OR IGNORE INTO never_play (user, track) VALUES (?, ?)',
                     (user.user_id, track))
    return Response(None, 200)


@app.route('/dislikes')
def route_dislikes():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        rows = conn.execute('''
                            SELECT playlist, track
                            FROM never_play JOIN track on never_play.track = track.path
                            WHERE user=?
                            ''', (user.user_id,)).fetchall()
        tracks = [{'path': path,
                   'playlist': playlist,
                   'title': metadata.cached(conn, path).display_title()}
                  for playlist, path in rows]

    return render_template('dislikes.jinja2',
                           csrf_token=csrf_token,
                           tracks=tracks)


@app.route('/dislikes_remove', methods=['POST'])
def route_dislikes_remove():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        conn.execute('DELETE FROM never_play WHERE user=? AND track=?',
                     (user.user_id, request.form['track']))

    return redirect('/dislikes')


@app.route('/never_play_json')
def route_never_play_json():
    """
    Return "never play" track paths in json format, for offline mode sync
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        rows = conn.execute('SELECT track FROM never_play WHERE user=?',
                            (user.user_id,)).fetchall()

    return {'tracks': [row[0] for row in rows]}


@app.route('/player_copy_track', methods=['POST'])
def route_player_copy_track():
    """
    Endpoint used by music player to copy a track to the user's primary playlist
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])
        playlist_name = request.json['playlist']

        playlist = music.user_playlist(conn, playlist_name, user.user_id)
        assert playlist.write or user.admin

        track = Track.by_relpath(conn, request.json['track'])

        if track.playlist == playlist.name:
            return Response(_('Track is already in this playlist'), content_type='text/plain')

        shutil.copy(track.path, playlist.path)

        scanner.scan_tracks(conn, playlist.name)

        return Response(None, 200)


@app.route('/install')
def route_install():
    return render_template('install.jinja2')


@app.route('/pwa')
def route_pwa():
    # Cannot have /player as an entrypoint directly, because for some reason the first request
    # to the start_url does not include cookies. Even a regular 302 redirect doesn't work!
    return '<meta http-equiv="refresh" content="0;URL=\'/player\'">'


@app.route('/health_check')
def route_health_check():
    return Response('ok', content_type='text/plain')


def is_mobile() -> bool:
    """
    Checks whether User-Agent looks like a mobile device (Android or iOS)
    """
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Android' in user_agent or 'iOS' in user_agent:
            return True
    return False


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    app.run(host='0.0.0.0', port=8080, debug=True)

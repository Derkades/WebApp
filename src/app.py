"""
Main application file, containing all Flask routes
"""
import logging
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection
from typing import Any
from urllib.parse import quote as urlencode

import bcrypt
from flask import (Flask, Response, redirect, render_template, request,
                   send_file)
from flask_babel import Babel, _, format_timedelta
from werkzeug.middleware.proxy_fix import ProxyFix

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
import radio
import scanner
import settings
from auth import AuthError, PrivacyOption, RequestTokenError
from charts import StatsPeriod
from image import ImageFormat, ImageQuality
from music import AudioType, Playlist, Track
from radio import RadioTrack

app = Flask(__name__, template_folder='templates')
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=settings.proxies_x_forwarded_for)
babel = Babel(app, locale_selector=language.get_locale)
log = logging.getLogger('app')
static_dir = Path('static')


@app.errorhandler(AuthError)
def handle_auth_error(err: AuthError):
    """
    Display permission denied error page with reason, or redirect to login page
    """
    if err.redirect:
        return redirect('/login')

    return Response(render_template('403.jinja2', reason=err.reason.message), 403)


@app.errorhandler(RequestTokenError)
def handle_token_error(_err: RequestTokenError):
    """
    Return bad request
    """
    log.warning('Invalid CSRF token')
    return Response('Invalid CSRF token', status=400, content_type='text/plain')


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


@app.route('/login', methods=['GET', 'POST'])
def route_login():
    """
    Login route. Serve login page for GET requests, and accepts password input for POST requests.
    If the provided password is invalid, the login template is rendered with invalid_password=True
    """
    with db.connect() as conn:
        try:
            auth.verify_auth_cookie(conn)
            # User is already logged in
            return redirect('/')
        except AuthError:
            pass

        if request.method == 'GET':
            return render_template('login.jinja2', invalid_password=False)

        if request.is_json:
            username = request.json['username']
            password = request.json['password']
        else:
            username = request.form['username']
            password = request.form['password']

        token = auth.log_in(conn, username, password)

        if token is None:
            if request.is_json:
                return Response(None, 403)
            else:
                return render_template('login.jinja2', invalid_password=True)

        if request.is_json:
            return {'token': token}

        response = redirect('/')
        response.set_cookie('token', token, max_age=3600*24*30, samesite='Strict')
        return response


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


@app.route('/get_csrf')
def route_get_csrf():
    """
    Get CSRF token
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
    response = jsonw.json_response({'token': csrf_token})
    response.cache_control.max_age = 600
    response.cache_control.private = True
    return response


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
def route_get_track() -> Response:
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
        return Response('Track does not exist', 404)

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
            return Response('No write permission for this playlist', 403)

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


@app.route('/download_search', methods=['POST'])
def route_download_search():
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        query = request.json['query']
        results = downloader.search(query)

    return {'results': results}


@app.route('/download')
def route_download():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        playlists = [(playlist.name, playlist.write)
                     for playlist in music.user_playlists(conn, user.user_id, all_writable=user.admin)]

    return render_template('download.jinja2',
                           csrf_token=csrf_token,
                           primary_playlist=user.primary_playlist,
                           playlists=playlists)


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


@app.route('/scan_music', methods=['POST'])
def route_scan_music():
    """
    Scans all playlists for new music
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        scanner.scan(conn)

    return Response(None, 200)


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


@app.route('/files')
def route_files():
    """
    File manager
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        csrf_token = user.get_csrf()

        if 'path' in request.args:
            browse_path = music.from_relpath(request.args['path'])
        else:
            browse_path = music.from_relpath('.')

        show_trashed = 'trash' in request.args

        if browse_path.resolve() == Path(settings.music_dir).resolve():
            parent_path = None
            write_permission = user.admin
        else:
            parent_path = music.to_relpath(browse_path.parent)
            # If the base directory is writable, all paths inside it will be, too.
            playlist = Playlist.from_path(conn, browse_path)
            write_permission = playlist.has_write_permission(user)

        children = []

        for path in browse_path.iterdir():
            if music.is_trashed(path) != show_trashed:
                continue

            file_info = {'path': music.to_relpath(path),
                         'name': path.name,
                         'type': 'dir' if path.is_dir() else 'file'}
            children.append(file_info)

            if path.is_dir():
                continue

            track = Track.by_relpath(conn, music.to_relpath(path))
            if track:
                meta = track.metadata()
                file_info['type'] = 'music'
                file_info['artist'] = ', '.join(meta.artists) if meta.artists else ''
                file_info['title'] = meta.title if meta.title else ''

    children = sorted(children, key=lambda x: x['name'])

    return render_template('files.jinja2',
                           base_path=music.to_relpath(browse_path),
                           parent_path=parent_path,
                           write_permission=write_permission,
                           files=children,
                           music_extensions=','.join(music.MUSIC_EXTENSIONS),
                           csrf_token=csrf_token,
                           show_trashed=show_trashed)


def check_filename(name: str) -> None:
    """
    Ensure file name is valid, if not raise ValueError
    """
    if '/' in name or name == '.' or name == '..':
        raise ValueError('illegal name')


@app.route('/playlists_create', methods=['POST'])
def route_playlists_create():
    """
    Form target to create playlist, called from /playlists page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])

        dir_name = request.form['path']

        check_filename(dir_name)

        path = Path(settings.music_dir, dir_name)

        if path.exists():
            return Response('Playlist path already exists', 400)

        path.mkdir()

        scanner.scan(conn)  # This creates a row for the playlist in the playlist table

        # New playlist should be writable for user who created it
        conn.execute('INSERT INTO user_playlist_write VALUES (user, playlist)',
                     (user.user_id, dir_name))

        return redirect('/playlists')


@app.route('/playlists_share', methods=['GET', 'POST'])
def route_playlists_share():
    if request.method == 'GET':
        with db.connect(read_only=True) as conn:
            auth.verify_auth_cookie(conn)
            usernames = [row[0] for row in conn.execute('SELECT username FROM user')]
        csrf = request.args['csrf']
        playlist_relpath = request.args['playlist']
        return render_template('playlists_share.jinja2',
                               csrf=csrf,
                               playlist=playlist_relpath,
                               usernames=usernames)

    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        playlist_relpath = request.form['playlist']
        username = request.form['username']

        target_user_id, = conn.execute('SELECT id FROM user WHERE username=?',
                                    (username,)).fetchone()

        # Verify playlist exists and user has write access
        playlist = music.user_playlist(conn, playlist_relpath, user.user_id)

        if not playlist.write and not user.admin:
            return Response('Cannot share playlist if you do not have write permission', 403)

        conn.execute('INSERT INTO user_playlist_write VALUES(?, ?) ON CONFLICT DO NOTHING',
                     (target_user_id, playlist_relpath))

        return redirect('/playlists')


@app.route('/files_upload', methods=['POST'])
def route_files_upload():
    """
    Form target to upload file, called from file manager
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])

        upload_dir = music.from_relpath(request.form['dir'])

        playlist = Playlist.from_path(conn, upload_dir)
        if not playlist.has_write_permission(user):
            return Response(None, 403)

    for uploaded_file in request.files.getlist('upload'):
        if uploaded_file.filename is None or uploaded_file.filename == '':
            return Response('Blank file name. Did you select a file?', 402, content_type='text/plain')

        check_filename(uploaded_file.filename)
        uploaded_file.save(Path(upload_dir, uploaded_file.filename))

    with db.connect() as conn:
        scanner.scan_tracks(conn, playlist.name)

    return redirect('/files?path=' + urlencode(music.to_relpath(upload_dir)))


@app.route('/files_rename', methods=['GET', 'POST'])
def route_files_rename():
    """
    Page and form target to rename file
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)

        if request.method == 'POST':
            if request.is_json:
                csrf = request.json['csrf']
                relpath = request.json['path']
                new_name = request.json['new_name']
            else:
                csrf = request.form['csrf']
                relpath = request.form['path']
                new_name = request.form['new-name']

            user.verify_csrf(csrf)

            path = music.from_relpath(relpath)
            check_filename(new_name)

            playlist = Playlist.from_path(conn, path)
            if not playlist.has_write_permission(user):
                return Response(None, 403)

            path.rename(Path(path.parent, new_name))

            scanner.scan_tracks(conn, playlist.name)

            if request.is_json:
                return Response(None, 200)
            else:
                return redirect('/files?path=' + urlencode(music.to_relpath(path.parent)))
        else:
            path = music.from_relpath(request.args['path'])
            back_url = request.args['back_url']
            return render_template('files_rename.jinja2',
                                csrf_token=user.get_csrf(),
                                path=music.to_relpath(path),
                                name=path.name,
                                back_url=back_url)


@app.route('/files_mkdir', methods=['POST'])
def route_files_mkdir():
    """
    Create directory, then enter it
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])

    path = music.from_relpath(request.form['path'])

    playlist = Playlist.from_path(conn, path)
    if not playlist.has_write_permission(user):
        return Response(None, 403)

    dirname = request.form['dirname']
    check_filename(dirname)
    Path(path, dirname).mkdir()
    return redirect('/files?path=' + urlencode(music.to_relpath(path)))


@app.route('/files_download')
def route_files_download():
    """
    Download track
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    path = music.from_relpath(request.args['path'])
    return send_file(path, as_attachment=True)


@app.route('/account')
def route_account():
    """
    Account information page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        sessions = user.sessions()

        result = conn.execute('SELECT name FROM user_lastfm WHERE user=?',
                              (user.user_id,)).fetchone()
        if result:
            lastfm_name, = result
        else:
            lastfm_name = None

    return render_template('account.jinja2',
                            user=user,
                            languages=language.LANGUAGES.items(),
                            csrf_token=csrf_token,
                            sessions=sessions,
                            lastfm_enabled=lastfm.is_configured(),
                            lastfm_name=lastfm_name,
                            lastfm_connect_url=lastfm.CONNECT_URL)


@app.route('/change_password_form', methods=['POST'])
def route_change_password_form():
    """
    Form target to change password, called from /account page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf_token'])
        if not user.verify_password(request.form['current_password']):
            return _('Incorrect password.')

        if request.form['new_password'] != request.form['repeat_new_password']:
            return _('Repeated new passwords do not match.')

        user.update_password(request.form['new_password'])
        return redirect('/')


@app.route('/change_nickname_form', methods=['POST'])
def route_change_nickname_form():
    """
    Form target to change nickname, called from /account page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf_token'])

        conn.execute('UPDATE user SET nickname=? WHERE id=?',
                     (request.form['nickname'], user.user_id))

    return redirect('/account')


@app.route('/change_language_form', methods=['POST'])
def route_change_language_form():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf_token'])

        lang_code = request.form['language']
        if lang_code == '':
            conn.execute('UPDATE user SET language = NULL')
        else:
            if lang_code not in language.LANGUAGES:
                return Response('Invalid language code', 400, content_type='text/plain')

            conn.execute('UPDATE user SET language=?',
                         (lang_code,))

    return redirect('/account')


@app.route('/change_privacy_setting', methods=['POST'])
def route_change_privacy_setting():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf_token'])

        privacy = request.form['privacy']
        assert privacy in {'none', 'aggregate', 'hidden'}

        if privacy == 'none':
            conn.execute('UPDATE user SET privacy = NULL')
        else:
            conn.execute('UPDATE user SET privacy = ?', (privacy,))

    return redirect('/account')


def radio_track_response(track: RadioTrack):
    return {
        'path': track.track.relpath,
        'start_time': track.start_time,
        'duration': track.duration,
    }


@app.route('/radio_current')
def route_radio_current():
    """
    Endpoint that returns information about the current radio track
    """
    with db.connect() as conn:
        auth.verify_auth_cookie(conn)
        track = radio.get_current_track(conn)
    return radio_track_response(track)


@app.route('/radio_next')
def route_radio_next():
    """
    Endpoint that returns information about the next radio track
    """
    with db.connect() as conn:
        auth.verify_auth_cookie(conn)
        track = radio.get_next_track(conn)
    return radio_track_response(track)


@app.route('/radio')
def route_radio_home():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token=user.get_csrf()
    return render_template('radio.jinja2',
                           csrf=csrf_token)


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


@app.route('/file_changes')
def route_file_changes():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        changes = get_file_changes_list(conn, 2000)

    return render_template('file_changes.jinja2',
                           changes=changes)


@app.route('/activity')
def route_activity():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

    return render_template('activity.jinja2')


@app.route('/activity_data')
def route_activity_data():
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


@app.route('/activity_all')
def route_activity_all():
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


@app.route('/playlist_stats')
def route_playlist_stats():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        playlists = music.playlists(conn)
        playlists_stats = [{'name': playlist.name,
                            'stats': playlist.stats()}
                           for playlist in playlists]

    return render_template('playlist_stats.jinja2',
                           playlists=playlists_stats)


@app.route('/playlists')
def route_playlists():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        user_playlists = music.user_playlists(conn, user.user_id)
        primary_playlist, = conn.execute('SELECT primary_playlist FROM user WHERE id=?',
                                         (user.user_id,)).fetchone()

    return render_template('playlists.jinja2',
                           user_is_admin=user.admin,
                           playlists=user_playlists,
                           csrf_token=csrf_token,
                           primary_playlist=primary_playlist)


@app.route('/playlists_favorite', methods=['POST'])
def route_playlists_favorite():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        playlist = request.form['playlist']
        is_favorite = request.form['favorite']
        if is_favorite == '1':
            conn.execute('INSERT INTO user_playlist_favorite VALUES (?, ?) ON CONFLICT DO NOTHING',
                         (user.user_id, playlist))
        else:
            conn.execute('DELETE FROM user_playlist_favorite WHERE user=? AND playlist=?',
                         (user.user_id, playlist))

    return redirect('/playlists')


@app.route('/playlists_set_primary', methods=['POST'])
def route_playlists_set_primary():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        playlist = request.form['primary-playlist']

        conn.execute('UPDATE user SET primary_playlist=? WHERE id=?',
                     (playlist, user.user_id))

    return redirect('/playlists')


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


@app.route('/users')
def route_users():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_admin=True)
        new_csrf_token = user.get_csrf()

        result = conn.execute('SELECT id, username, admin, primary_playlist FROM user')
        users = [{'id': user_id,
                  'username': username,
                  'admin': admin,
                  'primary_playlist': primary_playlist}
                 for user_id, username, admin, primary_playlist in result]

        for user_dict in users:
            result = conn.execute('SELECT playlist FROM user_playlist_write WHERE user=?',
                                  (user_dict['id'],))
            user_dict['writable_playlists'] = [playlist for playlist, in result]
            user_dict['writable_playlists_str'] = ', '.join(user_dict['writable_playlists'])

    return render_template('users.jinja2',
                           csrf_token=new_csrf_token,
                           users=users)


@app.route('/users_edit', methods=['GET', 'POST'])
def route_users_edit():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_admin=True)

        if request.method == 'GET':
            csrf_token = user.get_csrf()
            username = request.args['username']

            return render_template('users_edit.jinja2',
                                   csrf_token=csrf_token,
                                   username=username)
        else:
            user.verify_csrf(request.form['csrf'])
            username = request.form['username']
            new_username = request.form['new_username']
            new_password = request.form['new_password']

            if new_password != '':
                hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                conn.execute('UPDATE user SET password=? WHERE username=?',
                             (hashed_password, username))
                conn.execute('''
                             DELETE FROM session WHERE user = (SELECT id FROM user WHERE username=?)
                             ''', (username,))

            if new_username != username:
                conn.execute('UPDATE user SET username=? WHERE username=?',
                             (new_username, username))

            return redirect('/users')


@app.route('/users_new', methods=['POST'])
def route_users_new():
    form = request.form
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_admin=True)
        user.verify_csrf(form['csrf'])

    # Close connection, bcrypt hash takes a while
    username = form['username']
    password = form['password']
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    with db.connect() as conn:
        conn.execute('INSERT INTO user (username, password) VALUES (?, ?)',
                     (username, hashed_password))

    return redirect('/users')


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
            return Response(_('Track is already in this playlist'))

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

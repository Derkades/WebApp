from typing import Optional
import logging
from pathlib import Path
from urllib.parse import quote as urlencode
import random
import time

from flask import Flask, request, render_template, Response, redirect, send_file
from flask_babel import Babel
from flask_babel import _

import auth
from auth import AuthError, RequestTokenError
import bing
import db
import genius
import image
import lastfm
from metadata import Metadata
import music
from music import Playlist, Track, UserPlaylist
import musicbrainz
import radio
from radio import RadioTrack
import reddit
import scanner
import settings


app = Flask(__name__, template_folder='templates')
babel = Babel(app)
log = logging.getLogger('app')
assets_dir = Path('static')
raphson_png_path = Path(assets_dir, 'raphson.png')


LANGUAGES = (
    ('en', 'English'),
    ('nl', 'Nederlands'),
)


def pack_js(base_dir: Path):
    packed_js = b''
    for js_path in sorted(base_dir.iterdir()):
        with open(js_path, 'rb') as js_file:
            packed_js += js_file.read()
    return packed_js


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
    return Response('Invalid CSRF token', status=400)


@app.route('/')
def home():
    """
    Home page, with links to file manager and music player
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn, redirect_to_login=True)
    return render_template('home.jinja2')


@app.route('/login', methods=['GET', 'POST'])
def login():
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

        if request.method == 'POST':
            if 'password' not in request.form:
                return 'invalid form input'

            username = request.form['username']
            password = request.form['password']

            token = auth.log_in(conn, username, password)

            if token is None:
                return render_template('login.jinja2', invalid_password=True)

            response = redirect('/')
            response.set_cookie('token', token, max_age=3600*24*30, samesite='Strict')
            return response
        else:
            return render_template('login.jinja2', invalid_password=False)


@app.route('/player')
def player():
    """
    Main player page. Serves player.jinja2 template file.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        csrf_token = user.get_csrf()

    return render_template('player.jinja2',
                           mobile=is_mobile(),
                           csrf_token=csrf_token,
                           languages=LANGUAGES,
                           language=get_language())


PLAYER_JS = pack_js(Path('static', 'js', 'player'))


@app.route('/player.js')
def player_js():
    if settings.dev:
        # If debug is enabled, regenerate JS every request
        global PLAYER_JS
        PLAYER_JS = pack_js(Path('static', 'js', 'player'))

    return Response(PLAYER_JS, content_type='application/javascript')


@app.route('/get_csrf')
def get_csrf():
    """
    Get CSRF token
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
    return {'token': csrf_token}


@app.route('/choose_track', methods=['GET'])
def choose_track():
    """
    Choose random track from the provided playlist directory.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.args['csrf'])

        dir_name = request.args['playlist_dir']
        tag_mode = request.args['tag_mode']
        tags = request.args['tags'].split(';')
        playlist = music.playlist(conn, dir_name)
        chosen_track = playlist.choose_track(tag_mode=tag_mode, tags=tags)

    return {
        'path': chosen_track.relpath,
    }


@app.route('/get_track')
def get_track() -> Response:
    """
    Get transcoded audio for the given track path.
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])

    quality = request.args['quality'] if 'quality' in request.args else 'high'

    fruit = is_fruit()
    audio = track.transcoded_audio(quality, fruit)
    mime = 'audio/mp4' if fruit else 'audio/webm'
    response = Response(audio, mimetype=mime)
    response.accept_ranges = 'bytes'  # Workaround for Chromium bug https://stackoverflow.com/a/65804889
    return response


def get_cover_bytes(meta: Metadata, meme: bool) -> Optional[bytes]:
    """
    Find album cover using MusicBrainz or Bing.
    Parameters:
        meta: Track metadata
    Returns: Album cover image bytes, or None if MusicBrainz nor bing found an image.
    """
    log.info('Finding cover for: %s', meta.relpath)

    if meme:
        if random.random() > 0.4:
            query = next(meta.lyrics_search_queries())
            image_bytes = reddit.get_image(query)
            if image_bytes:
                return image_bytes

        query = next(meta.lyrics_search_queries()) + ' meme'
        if '-' in query:
            query = query[query.index('-')+1:]
        image_bytes = bing.image_search(query)
        if image_bytes:
            return image_bytes

    # Try MusicBrainz first
    mb_query = meta.album_release_query()
    if image_bytes := musicbrainz.get_cover(mb_query):
        return image_bytes

    # Otherwise try bing
    for query in meta.album_search_queries():
        if image_bytes := bing.image_search(query):
            return image_bytes

    log.info('No suitable cover found')
    return None


@app.route('/get_album_cover')
def get_album_cover() -> Response:
    """
    Get album cover image for the provided track path.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
        track = Track.by_relpath(conn, request.args['path'])
        meta = track.metadata()

    meme = 'meme' in request.args and bool(int(request.args['meme']))

    def get_img():
        img = get_cover_bytes(meta, meme)
        return img

    img_format = get_img_format()

    cache_id = track.relpath
    if meme:
        cache_id += 'meme2'

    comp_bytes = image.thumbnail(get_img, cache_id, img_format[6:], None,
                                 request.args['quality'], not meme)

    return Response(comp_bytes, mimetype=img_format)


@app.route('/get_lyrics')
def get_lyrics():
    """
    Get lyrics for the provided track path.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)

        track = Track.by_relpath(conn, request.args['path'])
        meta = track.metadata()

    for search_query in meta.lyrics_search_queries():
        lyrics = genius.get_lyrics(search_query)
        if lyrics is not None:
            return {
                'found': True,
                'source': lyrics.source_url,
                'html': lyrics.lyrics_html,
            }

    return {'found': False}


@app.route('/ytdl', methods=['POST'])
def ytdl():
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

    result = playlist.download(url)

    with db.connect() as conn:
        playlist = music.playlist(conn, directory)
        scanner.scan_tracks(conn, playlist.relpath)

    return {
        'code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
    }


@app.route('/track_list')
def track_list():
    """
    Return list of playlists and tracks.
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)

        playlists: list[UserPlaylist] = music.playlists(conn, user_id=user.user_id)

        response = {
            'playlists': {},
            'tracks': [],
        }

        for playlist in playlists:
            if playlist.track_count:
                response['playlists'][playlist.relpath] = {
                    'dir_name': playlist.relpath,
                    'display_name': playlist.name,
                    'track_count': playlist.track_count,
                    'favorite': playlist.favorite,
                    'write': playlist.write or user.admin,
                    'stats': playlist.stats(),
                }

        for playlist in playlists:
            for track in playlist.tracks():
                meta = track.metadata()
                response['tracks'].append({
                    'path': track.relpath,
                    'display': meta.display_title(),
                    'playlist': playlist.relpath,
                    'playlist_display': playlist.name,
                    'duration': meta.duration,
                    'tags': meta.tags,
                    'title': meta.title,
                    'artists': meta.artists,
                    'album': meta.album,
                    'album_artist': meta.album_artist,
                    'album_index': meta.album_index,
                    'year': meta.year,
                })

    return response


@app.route('/scan_music', methods=['POST'])
def scan_music():
    """
    Scans all playlists for new music
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        scanner.scan(conn)

    return Response(None, 200)


@app.route('/update_metadata', methods=['POST'])
def update_metadata():
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
            return Response('No write permission for this playlist', 403)

        track.write_metadata(title=payload['metadata']['title'],
                             album=payload['metadata']['album'],
                             artist='; '.join(payload['metadata']['artists']),
                             album_artist=payload['metadata']['album_artist'],
                             genre='; '.join(payload['metadata']['tags']),
                             date=payload['metadata']['year'])

    return Response(None, 200)


@app.route('/raphson')
def raphson() -> Response:
    """
    Serve raphson logo image
    """
    img_format = get_img_format()
    thumb = image.thumbnail(raphson_png_path, 'raphson', img_format[6:], 512, 'low', True)
    response = Response(thumb, mimetype=img_format)
    response.cache_control.max_age = 24*3600
    return response


@app.route('/files')
def files():
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

        if browse_path.resolve() == Path(settings.music_dir).resolve():
            parent_path_uri = None
            write_permission = user.admin
        else:
            parent_path_uri = urlencode(music.to_relpath(browse_path.parent))
            # If the base directory is writable, all paths inside it will be, too.
            playlist = Playlist.from_path(conn, browse_path)
            write_permission = playlist.has_write_permission(user)

        children = []

        for path in browse_path.iterdir():
            if path.name.startswith('.trash.'):
                continue

            file_info = {
                'path': music.to_relpath(path),
                'name': path.name,
            }
            children.append(file_info)

            if path.is_dir():
                file_info['type'] = 'dir'
            elif music.has_music_extension(path):
                file_info['type'] = 'music'
                track = Track.by_relpath(conn, music.to_relpath(path))
                meta = track.metadata()
                file_info['artist'] = ' & '.join(meta.artists) if meta.artists else ''
                file_info['title'] = meta.title if meta.title else ''
            else:
                file_info['type'] = 'file'

    children = sorted(children, key=lambda x: x['name'])

    return render_template('files.jinja2',
                           base_path=music.to_relpath(browse_path),
                           base_path_uri=urlencode(music.to_relpath(browse_path)),
                           write_permission=write_permission,
                           parent_path_uri=parent_path_uri,
                           files=children,
                           music_extensions=','.join(music.MUSIC_EXTENSIONS),
                           csrf_token=csrf_token)


def check_filename(name: str) -> None:
    """
    Ensure file name is valid, if not raise ValueError
    """
    if '/' in name or name == '.' or name == '..':
        raise ValueError('illegal name')


@app.route('/playlists_create', methods=['POST'])
def playlists_create():
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

        scanner.scan(conn)

        conn.execute('INSERT OR REPLACE INTO user_playlist (user, playlist, write) VALUES (?, ?, 1)',
                     (user.user_id, dir_name))

        return redirect('/playlists')


@app.route('/playlists_share', methods=['GET', 'POST'])
def playlists_share():
    if request.method == 'GET':
        with db.connect(read_only=True) as conn:
            auth.verify_auth_cookie(conn)
            usernames = [row[0] for row in conn.execute('SELECT username FROM user')]
        csrf = request.args['csrf']
        playlist = request.args['playlist']
        return render_template('playlists_share.jinja2',
                               csrf=csrf,
                               playlist=playlist,
                               usernames=usernames)
    else:
        with db.connect() as conn:
            user = auth.verify_auth_cookie(conn)
            user.verify_csrf(request.form['csrf'])
            playlist_relpath = request.form['playlist']
            username = request.form['username']

            target_user_id, = conn.execute('SELECT id FROM user WHERE username=?',
                                           (username,)).fetchone()

            # Verify playlist exists and user has write access
            playlist: UserPlaylist = music.playlist(conn, playlist_relpath, user_id=user.user_id)

            if not playlist.write and not user.admin:
                return Response('Cannot share playlist if you do not have write permission', 403)

            conn.execute('''
                         INSERT INTO user_playlist (user, playlist, write)
                         VALUES (?, ?, 1)
                         ON CONFLICT (user, playlist) DO UPDATE
                            SET write = 1
                         ''', (target_user_id, playlist_relpath))

            return redirect('/playlists')


@app.route('/files_upload', methods=['POST'])
def files_upload():
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
        check_filename(uploaded_file.filename)
        uploaded_file.save(Path(upload_dir, uploaded_file.filename))

    with db.connect() as conn:
        scanner.scan_tracks(conn, playlist.relpath)

    return redirect('/files?path=' + urlencode(music.to_relpath(upload_dir)))


@app.route('/files_rename', methods=['GET', 'POST'])
def files_rename():
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

            scanner.scan_tracks(conn, playlist.relpath)

            if request.is_json:
                return Response(None, 200)
            else:
                return redirect('/files?path=' + urlencode(music.to_relpath(path.parent)))
        else:
            path = music.from_relpath(request.args['path'])
            return render_template('files_rename.jinja2',
                                csrf_token=user.get_csrf(),
                                path=music.to_relpath(path),
                                name=path.name)


@app.route('/files_mkdir', methods=['POST'])
def files_mkdir():
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
def files_download():
    """
    Download track
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    path = music.from_relpath(request.args['path'])
    return send_file(path, as_attachment=True)


@app.route('/account')
def account():
    """
    Account information page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        sessions = user.sessions()

        return render_template('account.jinja2',
                               user=user,
                               csrf_token=csrf_token,
                               sessions=sessions,
                               lastfm_enabled=lastfm.is_configured(),
                               lastfm_name=user.lastfm_name,
                               lastfm_key=user.lastfm_key,
                               lastfm_connect_url=lastfm.CONNECT_URL)


@app.route('/change_password_form', methods=['POST'])
def change_password_form():
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
        return _('Password updated. All sessions have been invalidated. You will need to log in again.')


def radio_track_response(track: RadioTrack):
    return {
        'path': track.track.relpath,
        'start_time': track.start_time,
        'duration': track.duration,
    }


@app.route('/radio_current')
def radio_current():
    """
    Endpoint that returns information about the current radio track
    """
    with db.connect() as conn:
        auth.verify_auth_cookie(conn)
        track = radio.get_current_track(conn)
    return radio_track_response(track)


@app.route('/radio_next')
def radio_next():
    """
    Endpoint that returns information about the next radio track
    """
    with db.connect() as conn:
        auth.verify_auth_cookie(conn)
        track = radio.get_next_track(conn)
    return radio_track_response(track)


@app.route('/radio')
def radio_home():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token=user.get_csrf()
    return render_template('radio.jinja2',
                           csrf=csrf_token)


@app.route('/lastfm_callback')
def lastfm_callback():
    # After allowing access, last.fm sends the user to this page with an
    # authentication token. The authentication token can only be used once,
    # to obtain a session key. Session keys are stored in the database.

    # Cookies are not present here (because of cross-site redirect), so we
    # can't save the token just yet. Add another redirect step.

    auth_token = request.args['token']
    return render_template('lastfm_callback.jinja2',
                           auth_token=auth_token)


@app.route('/lastfm_connect', methods=['POST'])
def lastfm_connect():
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


@app.route('/now_playing', methods=['POST'])
def now_playing(read_only=True):
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        relpath = request.json['track']

        conn.execute('''
                     INSERT INTO now_playing (user, timestamp, track)
                     VALUES (:user_id, :timestamp, :relpath)
                     ON CONFLICT(user) DO UPDATE
                         SET timestamp=:timestamp, track=:relpath
                     ''',
                     {'user_id': user.user_id,
                      'timestamp': int(time.time()),
                      'relpath': relpath})

        user_key = lastfm.get_user_key(user)
        if not user_key:
            log.info('Skip last.fm now playing, account is not linked')
            return Response('ok', 200)

        track = Track.by_relpath(conn, relpath)
        meta = track.metadata()

    # Scrobble request takes a while, so close database connection first
    lastfm.update_now_playing(user_key, meta)
    return Response('ok', 200)


@app.route('/history_played', methods=['POST'])
def history_played():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])

        track = request.json['track']
        playlist = request.json['playlist']

        timestamp = int(time.time())
        conn.execute('''
                     INSERT INTO history (timestamp, user, track, playlist)
                     VALUES (?, ?, ?, ?)
                     ''',
                     (timestamp, user.user_id, track, playlist))

        if not request.json['lastfmEligible']:
            # No need to scrobble, nothing more to do
            return Response('ok', 200)

        lastfm_key = lastfm.get_user_key(user)

        if not lastfm_key:
            # User has not linked their account, no need to scrobble
            return Response('ok', 200)

        track = Track.by_relpath(conn, request.json['track'])
        meta = track.metadata()
        if meta is None:
            log.warning('Track is missing from database. Probably deleted by a rescan after the track was queued.')
            return Response('ok', 200)

    # Scrobble request takes a while, so close database connection first

    start_timestamp = request.json['startTimestamp']
    lastfm.scrobble(lastfm_key, meta, start_timestamp)

    return Response('ok', 200)


@app.route('/history')
def history():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        result = conn.execute('''
                              SELECT timestamp, username, playlist, track
                              FROM history LEFT JOIN user ON user = user.id
                              ORDER BY history.id DESC
                              LIMIT 50
                              ''')
        history_items = []
        for timestamp, username, playlist, relpath in result:
            track = Track.by_relpath(conn, relpath)
            meta = track.metadata()
            if meta is None:
                title = relpath
            else:
                title = meta.display_title()

            history_items.append({'time': timestamp,
                                  'username': username,
                                  'playlist': playlist,
                                  'title': title})

        result = conn.execute('''
                              SELECT username, playlist.name, track
                              FROM now_playing
                                JOIN user ON now_playing.user = user.id
                                JOIN track ON now_playing.track = track.path
                                JOIN playlist ON track.playlist = playlist.path
                              WHERE now_playing.timestamp > ?
                              ''',
                              (int(time.time()) - 185,))  # JS updates now playing every 3 minutes
        now_playing_items = []
        for username, playlist_name, relpath in result:
            track = Track.by_relpath(conn, relpath)
            meta = track.metadata()
            now_playing_items.append({'username': username,
                                      'playlist': playlist_name,
                                      'title': meta.display_title()})

    return render_template('history.jinja2',
                           history=history_items,
                           now_playing=now_playing_items)


@app.route('/playlists')
def playlists():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        user_playlists = music.playlists(conn, user_id=user.user_id)

    return render_template('playlists.jinja2',
                           user_is_admin=user.admin,
                           playlists=user_playlists,
                           csrf_token=csrf_token)


@app.route('/playlists_favorite', methods=['POST'])
def playlists_favorite():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        playlist = request.form['playlist']
        is_favorite = request.form['favorite']
        assert is_favorite in {'0', '1'}
        conn.execute('''
                     INSERT INTO user_playlist (user, playlist, favorite)
                     VALUES (?, ?, ?)
                     ON CONFLICT (user, playlist) DO UPDATE
                        SET favorite = ?
                     ''', (user.user_id, playlist, int(is_favorite), int(is_favorite)))

    return redirect('/playlists')


@app.route('/download')
def download():
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
        playlists = music.playlists(conn)

    return render_template('download.jinja2',
                           playlists=playlists)


def get_language() -> str:
    """
    Returns two letter language code, matching a language code in
    the LANGUAGES constant
    """
    if 'settings-language' in request.cookies:
        for language in LANGUAGES:
            if language[0] == request.cookies['settings-language']:
                return request.cookies['settings-language']

    best_match = request.accept_languages.best_match(['nl', 'nl-NL', 'nl-BE', 'en'])
    header_lang = best_match[:2] if best_match else 'en'
    return header_lang


@babel.localeselector
def get_locale():
    """
    Get locale preference from HTTP headers
    """
    return get_language()


def get_img_format():
    """
    Get preferred image format
    """
    if 'Accept' in request.headers:
        accept = request.headers['Accept']
        for mime in ['image-avif', 'image/webp']:
            if mime in accept:
                return mime

    # Once webp is working in Accept header for all image requests, this can be changed to jpeg
    # For now assume the browser supports WEBP to avoid always sending JPEG
    return 'image/webp'


def is_mobile() -> bool:
    """
    Checks whether User-Agent looks like a mobile device (Android or iOS)
    """
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Android' in user_agent or 'iOS' in user_agent:
            return True
    return False


def is_fruit() -> bool:
    """
    Check whether User-Agent looks like an Apple device
    """
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Macintosh' in user_agent or \
                'iPhone' in user_agent or \
                'iPad' in user_agent:
            return True
    return False


if __name__ == '__main__':
    import logconfig
    logconfig.apply()
    app.run(host='0.0.0.0', port='8080', debug=True)

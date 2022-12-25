from typing import Optional
import logging
from pathlib import Path
from urllib.parse import quote as urlencode
import random

from flask import Flask, request, render_template, Response, redirect, send_file
import flask_assets
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
from music import Track
import musicbrainz
import radio
from radio import RadioTrack
import reddit
import scanner


app = Flask(__name__, template_folder='templates')
babel = Babel(app)
flask_assets.Environment(app)
log = logging.getLogger('app')
assets_dir = Path('static')
raphson_png_path = Path(assets_dir, 'raphson.png')


LANGUAGES = (
    ('en', 'English'),
    ('nl', 'Nederlands'),
)


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
    with db.connect() as conn:
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

            token = auth.log_in(username, password)

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
                           user_is_admin=user.admin,
                           mobile=is_mobile(),
                           csrf_token=csrf_token,
                           languages=LANGUAGES,
                           language=get_language())


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
        chosen_track = playlist.choose_track(conn, tag_mode=tag_mode, tags=tags)

    return {
        'path': chosen_track.relpath,
    }


@app.route('/get_track')
def get_track() -> Response:
    """
    Get transcoded audio for the given track path.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.args['csrf'])

    quality = request.args['quality'] if 'quality' in request.args else 'high'

    track = Track.by_relpath(request.args['path'])
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
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.args['csrf'])

        track = Track.by_relpath(request.args['path'])
        meme = 'meme' in request.args and bool(int(request.args['meme']))

        def get_img():
            meta = track.metadata(conn)
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
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.args['csrf'])

        track = Track.by_relpath(request.args['path'])
        meta = track.metadata(conn)

    for search_query in meta.lyrics_search_queries():
        lyrics = genius.get_lyrics(search_query)
        if lyrics is not None:
            return {
                'found': True,
                'source': lyrics.source_url,
                'html': lyrics.lyrics_html(),
            }

    return {'found': False}


@app.route('/ytdl', methods=['POST'])
def ytdl():
    """
    Use yt-dlp to download the provided URL to a playlist directory
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_admin=True)
        user.verify_csrf(request.json['csrf'])

        directory = request.json['directory']
        url = request.json['url']

        playlist = music.playlist(conn, directory)
        log.info('ytdl %s %s', directory, url)

    result = playlist.download(url)

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
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.args['csrf'])

        playlists = music.playlists(conn)

        response = {
            'playlists': {},
            'tracks': [],
        }

        for playlist in playlists:
            response['playlists'][playlist.relpath] = {
                'dir_name': playlist.relpath,
                'display_name': playlist.name,
                'track_count': playlist.track_count,
                'guest': False,  # TODO remove when guest logic has been removed from frontend
            }

        for playlist in playlists:
            for track in playlist.tracks(conn):
                meta = track.metadata(conn)
                response['tracks'].append({
                    'path': track.relpath,
                    'display': meta.display_title(),
                    'display_file': meta.filename_title(),
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
        user = auth.verify_auth_cookie(conn, require_admin=True)
        user.verify_csrf(request.json['csrf'])

        if 'playlist' in request.json:
            playlist = music.playlist(conn, request.json['playlist'])
            scanner.scan_tracks(conn, playlist.relpath)
        else:
            playlists = scanner.scan_playlists(conn)
            for playlist in playlists:
                scanner.scan_tracks(conn, playlist)

    return Response(None, 200)


@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    """
    Endpoint to update track metadata
    """
    payload = request.json
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_admin=True)
        user.verify_csrf(payload['csrf'])

        track = Track.by_relpath(payload['path'])
        track.write_metadata(conn,
                            title=payload['metadata']['title'],
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
        base_path = music.from_relpath(request.args['path'])
        if base_path.as_posix() == '/music':
            parent_path_uri = None
        else:
            parent_path_uri = urlencode(music.to_relpath(base_path.parent))
    else:
        base_path = music.from_relpath('.')
        parent_path_uri = None

    children = []

    for path in base_path.iterdir():
        if path.name.startswith('.trash.'):
            continue

        can_delete = True
        if path.is_dir():
            pathtype = 'dir'
            try:
                next(path.iterdir())
                can_delete = False
            except StopIteration:
                pass
        elif music.has_music_extension(path):
            pathtype = 'music'
            can_delete = True
        else:
            pathtype = 'file'
        children.append({
            'path': music.to_relpath(path),
            'name': path.name,
            'type': pathtype,
            'can_delete': can_delete,
        })

    children = sorted(children, key=lambda x: x['name'])

    return render_template('files.jinja2',
                           base_path=music.to_relpath(base_path),
                           base_path_uri=urlencode(music.to_relpath(base_path)),
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


@app.route('/files_upload', methods=['POST'])
def files_upload():
    """
    Form target to upload file
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_admin=True)
        user.verify_csrf(request.form['csrf'])

    upload_dir = music.from_relpath(request.form['dir'])
    for uploaded_file in request.files.getlist('upload'):
        check_filename(uploaded_file.filename)
        uploaded_file.save(Path(upload_dir, uploaded_file.filename))
    return redirect('/files?path=' + urlencode(music.to_relpath(upload_dir)))


@app.route('/files_rename', methods=['GET', 'POST'])
def files_rename():
    """
    Page and form target to rename file
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_admin=True)

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
            path.rename(Path(path.parent, new_name))

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
        user = auth.verify_auth_cookie(conn, require_admin=True)
        user.verify_csrf(request.form['csrf'])

    path = music.from_relpath(request.form['path'])
    dirname = request.form['dirname']
    check_filename(dirname)
    Path(path, dirname).mkdir()
    return redirect('/files?path=' + urlencode(music.to_relpath(path)))


@app.route('/files_download')
def files_download():
    """
    Download track
    """
    with db.connect() as conn:
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
    with db.connect() as conn:
        auth.verify_auth_cookie(conn)
        track = radio.get_current_track(conn)
    return radio_track_response(track)


@app.route('/radio_next')
def radio_next():
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


@app.route('/lastfm_now_playing', methods=['POST'])
def lastfm_now_playing():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])
        track = Track.by_relpath(request.json['track'])
        lastfm.update_now_playing(user, track.metadata(conn))
    return Response('ok', 200)


@app.route('/lastfm_scrobble', methods=['POST'])
def lastfm_scrobble():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.json['csrf'])
        track = Track.by_relpath(request.json['track'])
        start_timestamp = request.json['start_timestamp']
        lastfm.scrobble(user, track.metadata(conn), start_timestamp)
    return Response('ok', 200)


def get_language() -> str:
    """
    Returns two letter language code, matching a language code in
    the LANGUAGES constant
    """
    if 'settings-language' in request.cookies:
        for language in LANGUAGES:
            if language[0] == request.cookies['settings-language']:
                return request.cookies['settings-language']

    header_lang = request.accept_languages.best_match(['nl', 'nl-NL', 'nl-BE', 'en'])[:2]
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
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Android' in user_agent or 'iOS' in user_agent:
            return True
    return False


def is_fruit() -> bool:
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Macintosh' in user_agent or \
                'iPhone' in user_agent or \
                'iPad' in user_agent:
            return True
    return False

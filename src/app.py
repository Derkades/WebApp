from typing import Optional
import logging
from pathlib import Path
from dataclasses import dataclass

from flask import Flask, request, render_template, Response, redirect
import flask_assets
from flask_babel import Babel
import bcrypt

import bing
import db
import genius
import image
from metadata import Metadata
import music
from music import Track
import musicbrainz
import scanner


app = Flask(__name__, template_folder='templates')
babel = Babel(app)
flask_assets.Environment(app)
log = logging.getLogger('app')
assets_dir = Path('static')
raphson_png_path = Path(assets_dir, 'raphson.png')


@dataclass
class User:
    username: str
    admin: bool


def check_password(username: Optional[str], password: Optional[str]) -> Optional[User]:
    """
    Check whether the provided password matches the correct password
    """
    if username is None or password is None:
        return None

    with db.users() as conn:
        result = conn.execute('SELECT password,admin FROM user WHERE username=?', (username,)).fetchone()

        if result is None:
            log.warning("Login attempt with non-existent username: '%s'", username)
            return None

        hashed_password, is_admin = result

        if not bcrypt.checkpw(password.encode(), hashed_password.encode()):
            return None

        return User(username, is_admin)


def check_password_cookie(require_admin: bool = False) -> Optional[User]:
    user = check_password(request.cookies.get('username'), request.cookies.get('password'))
    if require_admin and not user.admin:
        return None
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route. Serve login page for GET requests, and accepts password input for POST requests.
    If the provided password is invalid, the login template is rendered with invalid_password=True
    """
    if request.method == 'POST':
        if 'password' not in request.form:
            return 'invalid form input'

        username = request.form['username']
        password = request.form['password']

        if not check_password(username, password):
            return render_template('login.jinja2', invalid_password=True)

        response = redirect('/')
        response.set_cookie('username', username, max_age=3600*24*30, samesite='Strict')
        response.set_cookie('password', password, max_age=3600*24*30, samesite='Strict')
        return response
    else:
        if check_password_cookie():
            return redirect('/')

        return render_template('login.jinja2', invalid_password=False)


@app.route('/')
def player():
    """
    Main player page. Serves player.jinja2 template file.
    """
    user = check_password_cookie()
    if user is None:
        return redirect('/login')

    mobile = False
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Android' in user_agent or 'iOS' in user_agent:
            mobile = True

    return render_template('player.jinja2',
                           user_is_admin=user.admin,
                           mobile=mobile)


@app.route('/choose_track', methods=['GET'])
def choose_track():
    """
    Choose random track from the provided playlist directory.
    """
    if not check_password_cookie():
        return Response(None, 403)

    dir_name = request.args['playlist_dir']
    tag_mode = request.args['tag_mode']
    tags = request.args['tags'].split(';')
    playlist = music.playlist(dir_name)
    chosen_track = playlist.choose_track(tag_mode=tag_mode, tags=tags)

    return {
        'path': chosen_track.relpath,
    }


@app.route('/get_track')
def get_track() -> Response:
    """
    Get transcoded audio for the given track path.
    """
    if not check_password_cookie():
        return Response(None, 403)

    quality = request.args['quality'] if 'quality' in request.args else 'high'

    track = Track.by_relpath(request.args['path'])
    audio = track.transcoded_audio(quality)
    return Response(audio, mimetype='audio/ogg')


def get_cover_bytes(meta: Metadata) -> Optional[bytes]:
    """
    Find album cover using MusicBrainz or Bing.
    Parameters:
        meta: Track metadata
    Returns: Album cover image bytes, or None if MusicBrainz nor bing found an image.
    """
    log.info('Finding cover for: %s', meta.relpath)

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
    if not check_password_cookie():
        return Response(None, 403)

    track = Track.by_relpath(request.args['path'])

    def get_img():
        meta = track.metadata()
        img = get_cover_bytes(meta)
        return img

    img_format = get_img_format()

    comp_bytes = image.thumbnail(get_img, track.relpath, img_format[6:], 700,
                                 thumb_quality=request.args['quality'])

    return Response(comp_bytes, mimetype=img_format)


@app.route('/get_lyrics')
def get_lyrics():
    """
    Get lyrics for the provided track path.
    """
    if not check_password_cookie():
        return Response(None, 403)

    track = music.Track(request.args['path'])
    meta = track.metadata()

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
    if not check_password_cookie(require_admin=True):
        return Response(None, 403)

    directory = request.json['directory']
    url = request.json['url']

    playlist = music.playlist(directory)
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
    Return list of playlists and tracks. If it takes too long to load metadata for all tracks,
    a partial result is returned.
    """
    if not check_password_cookie():
        return Response(None, 403)

    response = {
        'playlists': {},
        'tracks': [],
    }

    playlists = music.playlists()

    for playlist in playlists:
        response['playlists'][playlist.relpath] = {
            'dir_name': playlist.relpath,
            'display_name': playlist.name,
            'track_count': playlist.track_count,
            'guest': playlist.guest,
        }

    for playlist in playlists:
        for track in playlist.tracks():
            meta = track.metadata()
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


@app.route('/scan_music')
def scan_music():
    """
    Scans all playlists for new music
    """
    if not check_password_cookie(require_admin=True):
        return Response(None, 403)

    if 'playlist' in request.args:
        scanner.rebuild_music_database(only_playlist=request.args['playlist'])
    else:
        scanner.rebuild_music_database()

    return Response(None, 200)


@app.route('/update_metadata', methods=['POST'])
def update_metadata():
    """
    Endpoint to update track metadata
    """
    if not check_password_cookie():
        return Response(None, 403)

    payload = request.get_json()
    track = Track(payload['path'])
    meta_dict = {
        'title': payload['metadata']['title'],
        'album': payload['metadata']['album'],
        'artist': '/'.join(payload['metadata']['artists']),
        'album_artist': payload['metadata']['album_artist'],
        'genre': '/'.join(payload['metadata']['tags']),
    }
    track.write_metadata(meta_dict)

    return Response(None, 200)


@app.route('/raphson')
def raphson() -> Response:
    """
    Serve raphson logo image
    """
    if not check_password_cookie():
        return Response(None, 403)

    img_format = get_img_format()
    thumb = image.thumbnail(raphson_png_path, 'raphson', img_format[6:], 512)
    response = Response(thumb, mimetype=img_format)
    response.cache_control.max_age = 24*3600
    return response


@babel.localeselector
def get_locale():
    """
    Get locale preference from HTTP headers
    """
    # TODO language from cookie
    lang = request.accept_languages.best_match(['nl', 'nl-NL', 'nl-BE', 'en'])
    return lang[:2] if lang is not None else 'en'


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

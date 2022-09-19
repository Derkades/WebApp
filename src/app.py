from typing import Optional
import traceback
import hashlib
import hmac
from logging.config import dictConfig
import logging
from pathlib import Path
from datetime import datetime, timedelta

from flask import Flask, request, render_template, Response, redirect
from flask_babel import Babel

from assets import Assets
from music import Playlist, Track
import cache
import bing
import genius
import settings
import musicbrainz


dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': settings.log_level,
        'handlers': ['wsgi']
    },
    'disable_existing_loggers': False,
})


application = Flask(__name__, template_folder=Path('templates'))
babel = Babel(application)
assets = Assets()
log = logging.getLogger('app')
assets_dir = Path('static')


with open(Path(assets_dir, 'raphson.png'), 'rb') as raphson_png:
    raphson_webp = bing.webp_thumbnail(raphson_png.read())


def check_password(password: Optional[str]) -> bool:
    """
    Check whether the provided password matches the correct password
    """
    if password is None:
        return False

    # First hash passwords so they have the same length
    # otherwise compare_digest still leaks length

    hashed_pass = hashlib.sha256(password.encode()).digest()
    hashed_correct = hashlib.sha256(settings.web_password.encode()).digest()

    # Constant time comparison
    return hmac.compare_digest(hashed_pass, hashed_correct)


def check_password_cookie() -> bool:
    return check_password(request.cookies.get('password'))


@application.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route. Serve login page for GET requests, and accepts password input for POST requests.
    If the provided password is invalid, the login template is rendered with invalid_password=True
    """
    if request.method == 'POST':
        if 'password' not in request.form:
            return 'invalid form input'

        password = request.form['password']

        if not check_password(password):
            return render_template('login.jinja2', invalid_password=True)

        response = redirect('/')
        response.set_cookie('password', password, max_age=3600*24*30, samesite='Strict')
        return response
    else:
        return render_template('login.jinja2', invalid_password=False)


@application.route('/')
def player():
    """
    Main player page. Serves player.jinja2 template file.
    """
    if not check_password_cookie():
        return redirect('/login')

    return render_template('player.jinja2',
                           main_playlists=Playlist.get_main(),
                           guest_playlists=Playlist.get_guests(),
                           assets=assets.all_assets_dict())


@application.route('/choose_track', methods=['GET'])
def choose_track():
    """
    Choose random track from the provided playlist directory.
    """
    if not check_password_cookie():
        return Response(None, 403)

    dir_name = request.args['playlist_dir']
    playlist = Playlist.by_dir_name(dir_name)
    chosen_track = playlist.choose_track()
    display_name = chosen_track.metadata().display_title()

    return {
        'path': chosen_track.relpath(),
        'display_name': display_name,
    }


@application.route('/get_track')
def get_track() -> Response:
    """
    Get transcoded audio for the given track path.
    """
    if not check_password_cookie():
        return Response(None, 403)

    quality = request.args['quality'] if 'quality' in request.args else 'high'

    track = Track.by_relpath(request.args['track_path'])
    audio = track.transcoded_audio(quality)
    return Response(audio, mimetype='audio/ogg')


@application.route('/get_album_cover')
def get_album_cover() -> Response:
    """
    Get album cover image for the provided track path.
    """
    if not check_password_cookie():
        return Response(None, 403)

    track = Track.by_relpath(request.args['track_path'])

    cache_obj = cache.get('album_art', track.relpath())
    cached_data = cache_obj.retrieve()
    if cached_data is not None:
        log.info('Returning cached image')
        return Response(cached_data, mimetype='image/webp')

    meta = track.metadata()

    webp_bytes = None
    try:
        query = meta.album_release_query()
        log.info('Searching MusicBrainz: %s', query)
        webp_bytes = musicbrainz.get_webp_cover(query)
    except Exception:
        log.info('Error retrieving album art from musicbrainz')
        traceback.print_exc()

    if webp_bytes is None:
        for query in meta.album_search_queries():
            try:
                log.info('Searching bing: %s', query)
                webp_bytes = bing.image_search(query)
                break
            except Exception:
                log.info('No bing results')
                traceback.print_exc()

    if webp_bytes is None:
        webp_bytes = raphson_webp

    cache_obj.store(webp_bytes)
    return Response(webp_bytes, mimetype='image/webp')


@application.route('/get_lyrics')
def get_lyrics():
    """
    Get lyrics for the provided track path.
    """
    if not check_password_cookie():
        return Response(None, 403)

    track = Track.by_relpath(request.args['track_path'])
    meta = track.metadata()

    for search_query in meta.lyrics_search_queries():
        lyrics = genius.get_lyrics(search_query)
        if lyrics is not None:
            return {
                'found': True,
                'genius_url': lyrics.source_url,
                'html': lyrics.lyrics_html(),
            }

    return {'found': False}


@application.route('/ytdl', methods=['POST'])
def ytdl():
    """
    Use yt-dlp to download the provided URL to a playlist directory
    """
    if not check_password_cookie():
        return Response(None, 403)

    directory = request.json['directory']
    url = request.json['url']

    playlist = Playlist.by_dir_name(directory)
    log.info('ytdl %s %s', directory, url)

    result = playlist.download(url)

    return {
        'code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
    }


@application.route('/search_track')
def search_track():
    """
    Search playlist directories for the provided query
    """
    if not check_password_cookie():
        return Response(None, 403)

    query = request.args['query']
    results = []
    for playlist in Playlist.get_all():
        for track in playlist.search_tracks(query):
            results.append({
                'playlist_dir': playlist.dir_name,
                'playlist_display': playlist.display_name,
                'track_file': track.name(),
                'track_display': track.metadata().display_title(),
            })
    return {
        'search_results': results
    }


@application.route('/track_list')
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
        'index': 0,
        'partial': False,
    }

    playlists = Playlist.get_all()

    for playlist in playlists:
        response['playlists'][playlist.dir_name] = {
            'dir_name': playlist.dir_name,
            'display_name': playlist.display_name,
            'track_count': playlist.count_tracks(),
            'guest': playlist.is_guest,
        }

    max_seconds = 5
    skip_to_index = int(request.args['skip']) if 'skip' in request.args else 0
    start_time = datetime.now()

    for playlist in playlists:
        for track in playlist.tracks():
            if skip_to_index <= response['index']:
                meta = track.metadata()
                response['tracks'].append({
                    'playlist': playlist.dir_name,
                    'playlist_display': playlist.display_name,
                    'file': track.relpath(),
                    'display': meta.display_title(),
                })

            if datetime.now() - start_time > timedelta(seconds=max_seconds):
                response['partial'] = True
                return response

            response['index'] += 1

    return response


@application.route('/style.css')
def style() -> Response:
    """
    Serve stylesheet, with placeholders replaced
    """
    if not check_password_cookie():
        return Response(None, 403)

    with open(Path(assets_dir, 'style.css'), 'rb') as style_file:
        stylesheet: bytes = style_file.read()
        stylesheet = stylesheet.replace(b'[[FONT_BASE64]]',
                                        assets.get_asset_b64('quicksand-v30-latin-regular.woff2').encode())
    return Response(stylesheet, mimetype='text/css')


@application.route('/raphson')
def raphson() -> Response:
    """
    Serve raphson logo image
    """
    if not check_password_cookie():
        return Response(None, 403)
    
    response = Response(raphson_webp, mimetype='image/webp')
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

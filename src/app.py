from typing import Optional
import traceback
import hashlib
import json
import hmac
from logging.config import dictConfig
import logging
from pathlib import Path

from flask import Flask, request, render_template, Response, redirect
from flask_babel import Babel

from assets import Assets
from music import Person
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
    if not check_password_cookie():
        return redirect('/login')

    return render_template('player.jinja2',
                           raphson=Person.get_main(),
                           guests=Person.get_guests(),
                           assets=assets.all_assets_dict())


@application.route('/choose_track', methods=['GET'])
def choose_track():
    if not check_password_cookie():
        return Response(None, 403)

    dir_name = request.args['person_dir']
    person = Person.by_dir_name(dir_name)
    chosen_track = person.choose_track()
    display_name = chosen_track.metadata().display_title()

    return {
        'name': chosen_track.name(),
        'display_name': display_name,
    }


@application.route('/get_track')
def get_track() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    quality = request.args['quality'] if 'quality' in request.args else 'high'

    person = Person.by_dir_name(request.args['person_dir'])
    track = person.track(request.args['track_name'])
    audio = track.transcoded_audio(quality)
    return Response(audio, mimetype='audio/ogg')


@application.route('/get_album_cover')
def get_album_cover() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    person = Person.by_dir_name(request.args['person_dir'])
    track = person.track(request.args['track_name'])

    cache_obj = cache.get('album_art', person.dir_name + track.name())
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
    if not check_password_cookie():
        return Response(None, 403)

    person = Person.by_dir_name(request.args['person_dir'])
    track = person.track(request.args['track_name'])

    cache_object = cache.get('genius2', person.dir_name + track.name())
    cached_data = cache_object.retrieve()

    if cached_data is not None:
        log.info('Returning cached lyrics')
        return Response(cached_data, mimetype='application/json')

    meta = track.metadata()

    genius_url = None
    for genius_query in meta.lyrics_search_queries():
        log.info('Searching genius: %s', genius_query)
        try:
            genius_url = genius.search(genius_query)
        except Exception:
            log.info('Search error')
            traceback.print_exc()
        if genius_url is not None:
            log.info('found genius url: %s', genius_url)
            break

    if genius_url is None:
        log.info('Genius search yielded no results')
        genius_json = {
            'found': False,
        }
    else:
        try:
            lyrics = genius.extract_lyrics(genius_url)
            genius_json = {
                'found': True,
                'genius_url': genius_url,
                'html': '<br>\n'.join(lyrics)
            }
        except Exception:
            log.info('Error retrieving lyrics')
            traceback.print_exc()
            # Return not found now, but don't cache so we try again in the future when the bug is fixed
            return {
                'found': False
            }

    json_bytes = json.dumps(genius_json).encode()
    cache_object.store(json_bytes)

    return Response(json_bytes, mimetype='application/json')


@application.route('/ytdl', methods=['POST'])
def ytdl():
    if not check_password_cookie():
        return Response(None, 403)

    directory = request.json['directory']
    url = request.json['url']

    person = Person.by_dir_name(directory)
    log.info('ytdl %s %s', directory, url)

    result = person.download(url)

    return {
        'code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
    }


@application.route('/search_track')
def search_track():
    if not check_password_cookie():
        return Response(None, 403)

    query = request.args['query']
    results = []
    for person in Person.get_all():
        for track in person.search_tracks(query):
            results.append({
                'person_dir': person.dir_name,
                'person_display': person.display_name,
                'track_file': track.name(),
                'track_display': track.metadata().display_title(),
            })
    return {
        'search_results': results
    }


@application.route('/track_list')
def track_list():
    if not check_password_cookie():
        return Response(None, 403)

    response = {'persons': []}
    for person in Person.get_all():
        person_json = {
            'dir_name': person.dir_name,
            'display_name': person.display_name,
            'tracks': [],
        }
        for track in person.tracks():
            person_json['tracks'].append({
                'file': track.name(),
                'display': track.metadata().display_title(),
            })
        response['persons'].append(person_json)

    return response


@application.route('/style.css')
def style() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    with open(Path(assets_dir, 'style.css'), 'rb') as style_file:
        stylesheet: bytes = style_file.read()
        stylesheet = stylesheet.replace(b'[[FONT_BASE64]]',
                                        assets.get_asset_b64('quicksand-v30-latin-regular.woff2').encode())
    return Response(stylesheet, mimetype='text/css')


@application.route('/raphson')
def raphson() -> Response:
    if not check_password_cookie():
        return Response(None, 403)
    return Response(raphson_webp, mimetype='image/webp')


@babel.localeselector
def get_locale():
    # TODO language from cookie
    lang = request.accept_languages.best_match(['nl', 'nl-NL', 'nl-BE', 'en'])
    return lang[:2] if lang is not None else 'en'

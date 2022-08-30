from typing import Optional
import traceback
import hashlib
import json
import hmac

from flask import Flask, request, render_template, send_file, Response, redirect

from assets import Assets
from music import Person
import cache
import bing
import genius
import settings
import musicbrainz


application = Flask(__name__)
assets = Assets()

with open('raphson.png', 'rb') as f:
    raphson_webp = bing.webp_thumbnail(f.read())


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
            return 'Invalid password. <a href="/login">Try again</a>'

        response = redirect('/')
        response.set_cookie('password', password, max_age=3600*24*30)
        return response
    else:
        return render_template('login.jinja2')


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

    print('Chosen track:', person.dir_name, chosen_track.name(), flush=True)
    print('Display name:', display_name, flush=True)

    return {
        'name': chosen_track.name(),
        'display_name': display_name,
    }


@application.route('/get_track')
def get_track() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    person = Person.by_dir_name(request.args['person_dir'])
    track = person.track(request.args['track_name'])
    audio = track.transcoded_audio()
    return Response(audio, mimetype='audio/ogg')


@application.route('/get_album_cover')
def get_album_cover() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    person = Person.by_dir_name(request.args['person_dir'])
    track = person.track(request.args['track_name'])

    cache_obj = cache.get('album_art', person.dir_name + track.name())
    if cache_obj.exists():
        print('Returning cached image', flush=True)
        return Response(cache_obj.retrieve(), mimetype='image/webp')

    meta = track.metadata()

    webp_bytes = None
    try:
        query = meta.album_release_query()
        print('Searching MusicBrainz:', query, flush=True)
        webp_bytes = musicbrainz.get_webp_cover(query)
    except Exception:
        print('Error retrieving album art from musicbrainz', flush=True)
        traceback.print_exc()

    if webp_bytes is None:
        for query in meta.album_search_queries():
            try:
                print('Searching bing:', query, flush=True)
                webp_bytes = bing.image_search(query)
                break
            except Exception:
                print('No bing results', flush=True)
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

    if cache_object.exists():
        print('Returning cached lyrics', flush=True)
        return send_file(cache_object.path, mimetype='application/json')

    meta = track.metadata()

    genius_url = None
    for genius_query in meta.lyrics_search_queries():
        print('Searching genius:', genius_query, flush=True)
        try:
            genius_url = genius.search(genius_query)
        except Exception:
            print('Search error')
            traceback.print_exc()
        if genius_url is not None:
            print('found genius url:', genius_url, flush=True)
            break

    if genius_url is None:
        print('genius search yielded no results', flush=True)
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
            print('Error retrieving lyrics', flush=True)
            traceback.print_exc()
            # Return not found now, but don't cache so we try again in the future when the bug is fixed
            return {
                'found': False
            }

    with open(cache_object.path, 'w', encoding='utf-8') as f:
        json.dump(genius_json, f)

    return send_file(cache_object.path, mimetype='application/json')


@application.route('/ytdl', methods=['POST'])
def ytdl():
    if not check_password_cookie():
        return Response(None, 403)

    directory = request.json['directory']
    url = request.json['url']

    person = Person.by_dir_name(directory)
    print('ytdl', directory, url, flush=True)

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



@application.route('/style.css')
def style() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    with open('style.css', 'rb') as f:
        stylesheet: bytes = f.read()
        stylesheet = stylesheet.replace(b'[[FONT_BASE64]]',
                                        assets.get_asset_b64('quicksand-v30-latin-regular.woff2').encode())
    return Response(stylesheet, mimetype='text/css')


@application.route('/script.js')
def script() -> Response:
    if not check_password_cookie():
        return Response(None, 403)
    return send_file('script.js')


@application.route('/raphson')
def raphson() -> Response:
    if not check_password_cookie():
        return Response(None, 403)
    return Response(raphson_webp, mimetype='image/webp')

from typing import Optional
import subprocess
import traceback
import hashlib
import json
import hmac
from pathlib import Path

from flask import Flask, request, render_template, send_file, Response, redirect

from assets import Assets
from music import Person
from cache import Cache
import bing
import settings


application = Flask(__name__)
assets = Assets()
cache = Cache(Path(settings.cache_dir))

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
    meta = person.get_track_metadata(chosen_track)

    return {
        'name': chosen_track,
        'display_name': meta.display_title()
    }


def transcode(input_file: Path) -> bytes:
    cache_object = cache.get('transcoded audio', input_file.absolute().as_posix())

    if cache_object.exists():
        print('Returning cached audio', flush=True)
        return cache_object.retrieve()

    # 1. Stilte aan het begin weghalen met silenceremove: https://ffmpeg.org/ffmpeg-filters.html#silenceremove
    # 2. Audio omkeren
    # 3. Stilte aan het eind (nu begin) weghalen
    # 4. Audio omkeren
    # 5. Audio normaliseren met dynaudnorm: https://ffmpeg.org/ffmpeg-filters.html#dynaudnorm

    # Nu zou je zeggen dat we ook stop_periods kunnen gebruiken om stilte aan het eind weg te halen, maar
    # dat werkt niet. Van sommige nummers (bijv. irrenhaus) werd alles eraf geknipt behalve de eerste paar
    # seconden. Ik heb geen idee waarom, de documentatie is vaag. Oplossing: keer het nummer om, en haal
    # nog eens stilte aan "het begin" weg.

    filters = '''
    silenceremove=start_periods=1:start_threshold=-50dB,
    areverse,
    silenceremove=start_periods=1:start_threshold=-50dB,
    areverse,
    dynaudnorm=peak=0.5
    '''

    # Remove whitespace and newlines
    filters = ''.join(filters.split())

    # with tempfile.NamedTemporaryFile() as temp:
    command = ['ffmpeg',
            '-y',  # overwrite existing file
            '-hide_banner',
            '-loglevel', settings.ffmpeg_loglevel,
            '-i', input_file.absolute().as_posix(),
            '-map_metadata', '-1',  # browser heeft metadata niet nodig
            '-c:a', 'libopus',
            '-b:a', settings.opus_bitrate,
            '-f', 'opus',
            '-vbr', 'on',
            '-t', settings.max_duration,
            '-filter:a', filters,
            cache_object.path]
    subprocess.check_output(command, shell=False)

    return cache_object.retrieve()


@application.route('/get_track')
def get_track() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    person_dir_name = request.args['person_dir']
    person = Person.by_dir_name(person_dir_name)
    track_name = request.args['track_name']
    file_path = person.get_track_path(track_name)

    do_transcode = True
    if do_transcode:
        audio = transcode(file_path)
        # We can't use send_file here, because the temp file is
        # automatically deleted once outside of the 'with' block
        # Read the entire file and send it in one go, instead.
        return Response(audio, mimetype='audio/ogg')
    else:
        return send_file(file_path)


@application.route('/get_album_cover')
def get_album_cover() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    person = Person.by_dir_name(request.args['person_dir'])
    track_name = request.args['track_name']
    meta = person.get_track_metadata(track_name)

    cache_obj = cache.get('bing2', person.dir_name + track_name)
    if cache_obj.exists():
        print('Returning cached bing image', flush=True)
        return Response(cache_obj.retrieve(), mimetype='image/webp')

    webp_bytes = None
    for bing_query in meta.album_search_queries():
        try:
            print('Searching bing:', bing_query, flush=True)
            webp_bytes = bing.image_search(bing_query)
            break
        except Exception:
            print('No results', flush=True)
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
    track_name = request.args['track_name']
    meta = person.get_track_metadata(track_name)

    cache_object = cache.get('genius2', person.dir_name + track_name)

    if cache_object.exists():
        print('Returning cached lyrics', flush=True)
        return send_file(cache_object.path, mimetype='application/json')

    genius_url = None
    for genius_query in meta.lyrics_search_queries():
        print('Searching genius:', genius_query, flush=True)
        try:
            genius_url = bing.genius_search(genius_query)
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
            lyrics = bing.genius_extract_lyrics(genius_url)
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


@application.route('/style.css')
def style() -> Response:
    with open('style.css', 'rb') as f:
        style: bytes = f.read()
        style = style.replace(b'[[FONT_BASE64]]', assets.get_asset_b64('quicksand-v30-latin-regular.woff2').encode())

    return Response(style, mimetype='text/css')


@application.route('/script.js')
def script() -> Response:
    return send_file('script.js')


@application.route('/raphson')
def raphson() -> Response:
    return send_file('raphson.png')

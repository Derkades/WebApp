from typing import Optional
import subprocess
import traceback
import hashlib
import tempfile
import hmac
from pathlib import Path

from flask import Flask, request, render_template, send_file, Response, redirect

from assets import Assets
from music import Person
import bing
import settings


application = Flask(__name__)
assets = Assets()


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

    dir_name = request.args['person']
    person = Person.by_dir_name(dir_name)
    chosen_track = person.choose_track()

    return {
        'name': chosen_track
    }


def transcode(input_file: Path) -> bytes:
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
    dynaudnorm
    '''

    # Remove whitespace and newlines
    filters = ''.join(filters.split())

    with tempfile.NamedTemporaryFile() as temp:
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
                temp.name]
        subprocess.check_output(command, shell=False)
        return temp.read()


@application.route('/get_track')
def get_track() -> Response:
    if not check_password_cookie():
        return Response(None, 403)

    person_dir_name = request.args['person']
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

    song_title = request.args['song_title']
    bing_query = bing.title_to_query(song_title)
    print('Original title:', song_title, flush=True)
    print('Bing title:', bing_query, flush=True)

    try:
        return Response(bing.image_search(bing_query + ' album cover'), mimetype='image/webp')
    except Exception:
        print('No bing results for album cover', flush=True)
        traceback.print_exc()

    try:
        return Response(bing.image_search(bing_query), mimetype='image/webp')
    except Exception:
        print('No bing results', flush=True)
        traceback.print_exc()

    return send_file('raphson.png')


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
    return send_file('style.css')


@application.route('/script.js')
def script() -> Response:
    return send_file('script.js')


@application.route('/raphson')
def raphson() -> Response:
    return send_file('raphson.png')

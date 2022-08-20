from flask import Flask, request, render_template, send_file, Response, redirect
import subprocess
from pathlib import Path
import os
import random
from bs4 import BeautifulSoup
import traceback
import requests
import json
import re
from io import BytesIO
from PIL import Image
import mimetypes
from datetime import datetime, timedelta
import hmac
from hmac import HMAC
import hashlib
import tempfile

application = Flask(__name__)

music_dir = Path('/music')

last_played = {}


def check_password(password: str) -> bool:
    if password is None:
        return False

    # First hash passwords so they have the same length
    # otherwise compare_digest still leaks length

    hashed_pass = hashlib.sha256()
    hashed_pass.update(password.encode())
    hashed_pass = hashed_pass.digest()

    hashed_correct = hashlib.sha256()
    hashed_correct.update(os.environ['WEB_PASSWORD'].encode())
    hashed_correct = hashed_correct.digest()

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

    guests = [d.name[6:] for d in Path(music_dir).iterdir() if d.name.startswith('Guest-')]
    return render_template('player.jinja2',
                           guests=guests)


@application.route('/choose_track', methods=['GET'])
def choose_track():
    if not check_password_cookie():
        return Response(None, 403)

    person = request.args['person']
    person_dir = Path(music_dir, person)
    tracks = [f.name for f in person_dir.iterdir() if os.path.isfile(f)]
    for attempt in range(10):
        chosen_track = random.choice(tracks)
        if chosen_track in last_played:
            if datetime.now() - last_played[chosen_track] < timedelta(hours=2):
                print(chosen_track, 'was played recently, picking a new song', flush=True)
                continue
        break

    last_played[chosen_track] = datetime.now()

    return {
        'name': chosen_track
    }


def transcode(input_file: Path, output_file: str) -> bytes:
    command = ['ffmpeg',
               '-y',  # overwrite existing file
               '-hide_banner',
               '-loglevel', 'info',
               '-i', input_file.absolute().as_posix(),
               '-c:a', 'libopus',
               '-b:a', '96K',
               '-f', 'opus',
               '-vbr', 'on',
               '-filter:a', 'silenceremove=start_periods=1:stop_periods=1:start_threshold=-90dB:stop_threshold=-90dB:detection=1,dynaudnorm=p=0.5',
               output_file]
    subprocess.check_output(command, shell=False)


@application.route('/get_track')
def get_track():
    if not check_password_cookie():
        return Response(None, 403)

    person = request.args['person']
    track_name = request.args['track_name']
    file_path = Path(music_dir, person, track_name)

    do_transcode = True
    if do_transcode:
        temp: BytesIO
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            transcode(file_path, temp.name)
            # We can't use send_file here, because the temp file is automatically deleted once outside of the 'with' block
            # Read the entire file and send it in one go, instead.
            return Response(temp.read(), mimetype='audio/ogg')
    else:
        return send_file(file_path)


def bing_search_image(bing_query: str) -> bytes:
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0'}
    r = requests.get('https://www.bing.com/images/search',
                     headers=headers,
                     params={'q': bing_query,
                             'form': 'HDRSC2',
                             'first': '1',
                             'scenario': 'ImageBasicHover'})
    soup = BeautifulSoup(r.text, 'html.parser')
    data = soup.find_all('a', {'class': 'iusc'})[0]
    json_data = json.loads(data['m'])
    img_link = json_data['murl']
    r = requests.get(img_link, headers=headers)
    return r.content


def title_to_bing_query(title: str):
    print('Original title:', title, flush=True)
    title = title.lower()
    title = title.rstrip('.mp3').rstrip('.webm')  # Remove file extensions
    title = re.sub(r' \[[a-z0-9\-_]+\]', '', title)  # Remove youtube id suffix
    strip_keywords = [
        'monstercat release',
        'nerd nation release',
        'monstercat official music video',
        'official audio',
        'official video',
        'official music video',
        'official lyric video',
        'official hd video',
        'extended version',
        'long version',
        '[out now]',
        'clip officiel',
        'hq videoclip',
        'videoclip',
        '(visual)'
    ]
    for strip_keyword in strip_keywords:
        title = title.replace(strip_keyword, '')
    title = ''.join([c for c in title if c == ' ' or c == '-' or c >= 'a' and c <= 'z'])  # Remove special characters
    title = title.strip()
    print('Bing title:', title, flush=True)
    return title


@application.route('/get_album_cover')
def get_album_cover():
    if not check_password_cookie():
        return Response(None, 403)

    song_title = request.args['song_title']
    bing_query = title_to_bing_query(song_title)
    try:
        img_bytes = bing_search_image(bing_query)
        img = Image.open(BytesIO(img_bytes))
        img.thumbnail((1024, 1024), Image.ANTIALIAS)
        img_out = BytesIO()
        img.save(img_out, format='webp', quality=80)
        img_out.seek(0)
        return send_file(img_out, mimetype='image/webp')
    except:
        print('No bing results', flush=True)
        traceback.print_exc()
        return send_file('raphson.png')


@application.route('/style.css')
def style():
    return send_file('style.css')


@application.route('/script.js')
def script():
    return send_file('script.js')


@application.route('/raphson')
def raphson():
    return send_file('raphson.png')


# hieronder oude dingen voor youtube downloader, herimplementeren we later wel

# def constant_time_compare(val1, val2):
#     if len(val1) != len(val2):
#         return False
#     result = 0
#     for x, y in zip(val1, val2):
#         result |= x ^ y
#     return result == 0

# @app.route('/', methods=['POST'])
# def my_form_post():
#     if not constant_time_compare(request.form['wachtwoord'].encode(), b'dit zal nooit iemand raden'):
#         print(request.form['wachtwoord'].encode())
#         return 'NEE'

#     text = request.form['text']
#     persoon = request.form['persoon']
#     titel = request.form['titel']

#     if '/' in titel:
#         return 'mag geen / in titel'

#     if persoon not in ['DK', 'CB', 'JK']:
#         return 'verkeerde naam'

#     subprocess.check_output(['yt-dlp', '-f', '140', '-o', f'/downloads/{persoon}/{titel}.mp3', text], shell=False)
#     # processed_text = text.upper()
#     return 'gelukt <a href="/">nog een</a>'

# @app.route('/test')
# def list_names():
#     dirs = [d.name for d in music_dir.iterdir()]
#     return {'dirs': dirs}

# if __name__ == "__main__":
#     app.run(debug=False)

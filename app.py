from flask import Flask, request, render_template, send_file
import subprocess
from pathlib import Path
import random
from bs4 import BeautifulSoup
import traceback
import requests
import json
import re

app = Flask(__name__)

music_dir = Path('/music')


@app.route('/')
def player():
    guests = [d.name[6:] for d in Path(music_dir).iterdir() if d.name.startswith('Guest-')]
    return render_template('player.jinja2',
                           guests=guests)


@app.route('/style.css')
def style():
    return send_file('style.css')


@app.route('/script.js')
def script():
    return send_file('script.js')


@app.route('/choose_track', methods=['GET'])
def choose_track():
    person = request.args['person']
    person_dir = Path(music_dir, person)
    tracks = list(person_dir.iterdir())
    chosen_track = random.choice(tracks)
    return {
        'name': chosen_track.name
    }


@app.route('/get_track')
def get_track():
    person = request.args['person']
    track_name = request.args['track_name']
    return send_file(Path(music_dir, person, track_name))


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
    title = re.sub(r' \[[a-z0-9]{11}\]', '', title)  # Remove youtube id suffix
    title = re.sub(r' \[[a-z]+ release\]', '', title)  # Remove "[... release]"
    title = title.replace('official video', '')  # Remove "official video"
    title = ''.join([c for c in title if c == ' ' or c == '-' or c >= 'a' and c <= 'z'])  # Remove special characters
    title = title.strip()
    print('Bing title:', title, flush=True)
    return title


@app.route('/get_album_cover')
def get_album_cover():
    try:
        song_title = request.args['song_title']
        image = bing_search_image(title_to_bing_query(song_title))
        # TODO resize met iets van Image.open(BytesIO(image)).resize((IMAGE_SIZE, IMAGE_SIZE))
        # beter hier dan in frontend om de grootte van de afbeelding te verminderen, minder data verbruik en sneller
        # misschien zelfs overwegen wat sterke jpeg compressie toe te passen, de afbeelding is toch klein
        return image
    except:
        traceback.print_exc()
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

if __name__ == "__main__":
    app.run(debug=False)

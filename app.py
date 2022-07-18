# from flask import Flask

# app = Flask(__name__)

# @app.route("/")
# def hello() -> str:
#     return "Hello japser"


# if __name__ == "__main__":
#     app.run(debug=False)


from flask import Flask, request, render_template, send_file
import subprocess
from pathlib import Path
import random

app = Flask(__name__)

music_dir = Path('/music')

@app.route('/')
def player():
    return render_template('player.jinja2',
                           guests=[d.name for d in Path(music_dir, 'Gasten').iterdir()])

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

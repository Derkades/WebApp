from sqlite3 import Connection
from flask import Blueprint, abort, redirect, render_template, request
from flask_babel import gettext as _

from raphson_mp import auth, language, music
from raphson_mp.auth import PrivacyOption, User
from raphson_mp.decorators import route
from raphson_mp.theme import THEMES

bp = Blueprint('account', __name__, url_prefix='/account')


@route(bp, '')
def route_account(conn: Connection, user: User):
    """
    Account information page
    """
    from raphson_mp import lastfm

    sessions = user.sessions()

    result = conn.execute('SELECT name FROM user_lastfm WHERE user=?',
                            (user.user_id,)).fetchone()
    if result:
        lastfm_name, = result
    else:
        lastfm_name = None

    playlists = music.playlists(conn)

    return render_template('account.jinja2',
                            languages=language.LANGUAGES.items(),
                            sessions=sessions,
                            lastfm_enabled=lastfm.is_configured(),
                            lastfm_name=lastfm_name,
                            lastfm_connect_url=lastfm.get_connect_url(),
                            playlists=playlists,
                            themes=THEMES.items())


@route(bp, '/change_settings', methods=['POST'], write=True)
def route_change_settings(conn: Connection, user: User):
    nickname = request.form['nickname']
    lang_code = request.form['language']
    privacy = request.form['privacy']
    playlist = request.form['playlist']
    theme = request.form['theme']

    if nickname == '': nickname = None
    if playlist == '': playlist = None
    if lang_code == '': lang_code = None
    if privacy == '': privacy = None

    if lang_code not in language.LANGUAGES:
        abort(400, 'Invalid language code')

    if privacy not in PrivacyOption:
        abort(400, 'Invalid privacy option')

    if theme not in THEMES:
        abort(400, 'invalid theme')

    conn.execute('UPDATE user SET nickname=?, language=?, privacy=?, primary_playlist=?, theme=? WHERE id=?',
                    (nickname, lang_code, privacy, playlist, theme, user.user_id))

    return redirect('/account', code=303)


@route(bp, '/change_password', methods=['POST'], write=True)
def route_change_password(conn: Connection, user: User):
    """
    Form target to change password, called from /account page
    """
    if not auth.verify_password(conn, user.user_id, request.form['current_password']):
        abort(400, _('Incorrect password.'))

    if request.form['new_password'] != request.form['repeat_new_password']:
        abort(400, _('Repeated new passwords do not match.'))

    user.update_password(request.form['new_password'])
    return redirect('/', code=303)

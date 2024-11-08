from flask import Blueprint, abort, redirect, render_template, request
from flask_babel import gettext as _

from raphson_mp import auth, db, language, music
from raphson_mp.auth import PrivacyOption

bp = Blueprint('account', __name__, url_prefix='/account')


@bp.route('')
def route_account():
    """
    Account information page
    """
    from raphson_mp import lastfm

    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)
        csrf_token = user.get_csrf()
        sessions = user.sessions()

        result = conn.execute('SELECT name FROM user_lastfm WHERE user=?',
                              (user.user_id,)).fetchone()
        if result:
            lastfm_name, = result
        else:
            lastfm_name = None

        playlists = music.playlists(conn)

    return render_template('account.jinja2',
                            user=user,
                            languages=language.LANGUAGES.items(),
                            csrf_token=csrf_token,
                            sessions=sessions,
                            lastfm_enabled=lastfm.is_configured(),
                            lastfm_name=lastfm_name,
                            lastfm_connect_url=lastfm.get_connect_url(),
                            playlists=playlists)


@bp.route('/change_settings', methods=['POST'])
def route_change_settings():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        nickname = request.form['nickname']
        lang_code = request.form['language']
        privacy = request.form['privacy']
        playlist = request.form['playlist']

        if nickname == '': nickname = None
        if playlist == '': playlist = None
        if lang_code == '': lang_code = None
        if privacy == '': privacy = None

        if lang_code not in language.LANGUAGES:
            abort(400, 'Invalid language code')

        if privacy not in PrivacyOption:
            abort(400, 'Invalid privacy option')

        conn.execute('UPDATE user SET nickname=?, language=?, privacy=?, primary_playlist=? WHERE id=?',
                     (nickname, lang_code, privacy, playlist, user.user_id))

    return redirect('/account', code=303)


@bp.route('/change_password', methods=['POST'])
def route_change_password():
    """
    Form target to change password, called from /account page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        if not auth.verify_password(conn, user.user_id, request.form['current_password']):
            abort(400, _('Incorrect password.'))

        if request.form['new_password'] != request.form['repeat_new_password']:
            abort(400, _('Repeated new passwords do not match.'))

        user.update_password(request.form['new_password'])
        return redirect('/', code=303)

from flask import Blueprint, Response, redirect, render_template, request
from flask_babel import gettext as _

from raphson_mp import auth, db, language

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

    return render_template('account.jinja2',
                            user=user,
                            languages=language.LANGUAGES.items(),
                            csrf_token=csrf_token,
                            sessions=sessions,
                            lastfm_enabled=lastfm.is_configured(),
                            lastfm_name=lastfm_name,
                            lastfm_connect_url=lastfm.get_connect_url())


@bp.route('/change_password', methods=['POST'])
def route_change_password():
    """
    Form target to change password, called from /account page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        if not auth.verify_password(conn, user.user_id, request.form['current_password']):
            return _('Incorrect password.')

        if request.form['new_password'] != request.form['repeat_new_password']:
            return _('Repeated new passwords do not match.')

        user.update_password(request.form['new_password'])
        return redirect('/', code=303)


@bp.route('/change_nickname', methods=['POST'])
def route_change_nickname():
    """
    Form target to change nickname, called from /account page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        conn.execute('UPDATE user SET nickname=? WHERE id=?',
                     (request.form['nickname'], user.user_id))

    return redirect('/account', code=303)


@bp.route('/change_language', methods=['POST'])
def route_change_language():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        lang_code = request.form['language']
        if lang_code == '':
            conn.execute('UPDATE user SET language = NULL WHERE id=?', (user.user_id,))
        else:
            if lang_code not in language.LANGUAGES:
                return Response('Invalid language code', 400, content_type='text/plain')

            conn.execute('UPDATE user SET language=? WHERE id=?',
                         (lang_code, user.user_id))

    return redirect('/account', code=303)


@bp.route('/change_privacy_setting', methods=['POST'])
def route_change_privacy_setting():
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        privacy = request.form['privacy']
        assert privacy in {'none', 'aggregate', 'hidden'}

        if privacy == 'none':
            conn.execute('UPDATE user SET privacy = NULL WHERE id=?', (user.user_id,))
        else:
            conn.execute('UPDATE user SET privacy = ? WHERE id=?', (privacy, user.user_id))

    return redirect('/account', code=303)

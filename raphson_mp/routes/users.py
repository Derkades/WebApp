from sqlite3 import Connection
import time

from flask import Blueprint, redirect, render_template, request
from flask_babel import format_timedelta
from flask_babel import gettext as _

from raphson_mp import db
from raphson_mp import auth
from raphson_mp.auth import User
from raphson_mp.decorators import route

bp = Blueprint('users', __name__, url_prefix='/users')


@route(bp, '', redirect_to_login=True, require_admin=True)
def route_users(conn: Connection, user: User):
    """User list page"""
    result = conn.execute('''
                            SELECT user.id, username, admin, primary_playlist, MAX(last_use)
                            FROM user LEFT JOIN session ON user.id = session.user
                            GROUP BY user.id
                            ''')
    users = [{'id': user_id,
                'username': username,
                'admin': admin,
                'primary_playlist': primary_playlist,
                'last_use': last_use}
                for user_id, username, admin, primary_playlist, last_use in result]

    for user_dict in users:
        result = conn.execute('SELECT playlist FROM user_playlist_write WHERE user=?',
                                (user_dict['id'],))
        user_dict['writable_playlists'] = [playlist for playlist, in result]
        user_dict['writable_playlists_str'] = ', '.join(user_dict['writable_playlists'])
        if user_dict['last_use'] is None:
            user_dict['last_use'] = _('More than 30 days ago')
        else:
            user_dict['last_use'] = format_timedelta(user_dict['last_use'] - int(time.time()), add_direction=True)

    return render_template('users.jinja2',
                           users=users)


@route(bp, '/edit', methods=['GET', 'POST'], write=True, require_admin=True)
def route_edit(conn: Connection, _user: User):
    """Change username or password"""
    if request.method == 'GET':
        username = request.args['username']

        return render_template('users_edit.jinja2',
                                username=username)

    username = request.form['username']
    new_username = request.form['new_username']
    new_password = request.form['new_password']

    if new_password != '':
        hashed_password = auth.hash_password(new_password)
        conn.execute('UPDATE user SET password=? WHERE username=?',
                        (hashed_password, username))
        conn.execute('''
                        DELETE FROM session WHERE user = (SELECT id FROM user WHERE username=?)
                        ''', (username,))

    if new_username != username:
        conn.execute('UPDATE user SET username=? WHERE username=?',
                        (new_username, username))

    return redirect('/users', code=303)


@route(bp, '/new', methods=['POST'], write=True, require_admin=True)
def route_new(conn: Connection, _user: User):
    """Create new user"""
    # Close database connection, password hashing takes a while
    username = request.form['username']
    password = request.form['password']
    hashed_password = auth.hash_password(password)

    with db.connect() as conn:
        conn.execute('INSERT INTO user (username, password) VALUES (?, ?)',
                     (username, hashed_password))

    return redirect('/users', code=303)

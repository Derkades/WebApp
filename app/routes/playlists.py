from flask import Blueprint, abort, redirect, render_template, request

from app import auth, db, music, scanner, settings, util

bp = Blueprint('playlists', __name__, url_prefix='/playlists')


@bp.route('')
def route_playlists():
    """
    Playlist management page
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        csrf_token = user.get_csrf()
        user_playlists = music.user_playlists(conn, user.user_id)
        primary_playlist, = conn.execute('SELECT primary_playlist FROM user WHERE id=?',
                                         (user.user_id,)).fetchone()

        playlists_stats = [{'name': playlist.name,
                            'stats': playlist.stats()}
                           for playlist in user_playlists]

    return render_template('playlists.jinja2',
                           user_is_admin=user.admin,
                           playlists=user_playlists,
                           csrf_token=csrf_token,
                           primary_playlist=primary_playlist,
                           playlists_stats=playlists_stats)


@bp.route('/favorite', methods=['POST'])
def route_favorite():
    """
    Form target to mark a playlist as favorite.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        playlist = request.form['playlist']
        is_favorite = request.form['favorite']
        if is_favorite == '1':
            conn.execute('INSERT INTO user_playlist_favorite VALUES (?, ?) ON CONFLICT DO NOTHING',
                         (user.user_id, playlist))
        else:
            conn.execute('DELETE FROM user_playlist_favorite WHERE user=? AND playlist=?',
                         (user.user_id, playlist))

    return redirect('/playlists', code=303)


@bp.route('/set_primary', methods=['POST'])
def route_set_primary():
    """
    Form target to configure a primary playlist.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        playlist = request.form['primary-playlist']

        conn.execute('UPDATE user SET primary_playlist=? WHERE id=?',
                     (playlist, user.user_id))

    return redirect('/playlists', code=303)


@bp.route('/create', methods=['POST'])
def route_create():
    """
    Form target to create playlist, called from /playlists page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])

        dir_name = request.form['path']

        util.check_filename(dir_name)

        path = settings.music_dir / dir_name

        if path.exists():
            abort(400, 'Playlist path already exists')

        path.mkdir()

    # Database connection must be closed because scanner creates its own connection
    scanner.scan()  # This creates a row for the playlist in the playlist table

    with db.connect() as conn:
        # New playlist should be writable for user who created it
        conn.execute('INSERT INTO user_playlist_write VALUES (?, ?)',
                     (user.user_id, dir_name))

    return redirect('/playlists', code=303)


@bp.route('/share', methods=['GET', 'POST'])
def route_share():
    """
    GET: Page to select a username to share the provided playlist with
    POST: Form target to submit the selected username
    """
    if request.method == 'GET':
        with db.connect(read_only=True) as conn:
            auth.verify_auth_cookie(conn)
            usernames = [row[0] for row in conn.execute('SELECT username FROM user')]
        csrf = request.args['csrf']
        playlist_relpath = request.args['playlist']
        return render_template('playlists_share.jinja2',
                               csrf=csrf,
                               playlist=playlist_relpath,
                               usernames=usernames)

    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn)
        user.verify_csrf(request.form['csrf'])
        playlist_relpath = request.form['playlist']
        username = request.form['username']

        target_user_id, = conn.execute('SELECT id FROM user WHERE username=?',
                                    (username,)).fetchone()

        # Verify playlist exists and user has write access
        playlist = music.user_playlist(conn, playlist_relpath, user.user_id)

        if not playlist.write and not user.admin:
            abort(403, 'Cannot share playlist if you do not have write permission')

        conn.execute('INSERT INTO user_playlist_write VALUES(?, ?) ON CONFLICT DO NOTHING',
                     (target_user_id, playlist_relpath))

        return redirect('/playlists', code=303)

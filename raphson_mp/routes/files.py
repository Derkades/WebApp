from pathlib import Path
from urllib.parse import quote as urlencode

from flask import (Blueprint, Response, abort, redirect, render_template,
                   request, send_file)

from raphson_mp import auth, db, music, scanner, settings, util
from raphson_mp.music import Playlist, Track
from raphson_mp.util import send_directory

bp = Blueprint('files', __name__, url_prefix='/files')


@bp.route('')
def route_files():
    """
    File manager
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, redirect_to_login=True)
        csrf_token = user.get_csrf()

        if 'path' in request.args:
            browse_path = music.from_relpath(request.args['path'])
        else:
            browse_path = music.from_relpath('.')

        show_trashed = 'trash' in request.args

        if browse_path.resolve() == settings.music_dir.resolve():
            parent_path = None
            write_permission = user.admin
        else:
            parent_path = music.to_relpath(browse_path.parent)
            # If the base directory is writable, all paths inside it will be, too.
            playlist = Playlist.from_path(conn, browse_path)
            write_permission = playlist.has_write_permission(user)

        children = []

        for path in browse_path.iterdir():
            if music.is_trashed(path) != show_trashed:
                continue

            file_info = {'path': music.to_relpath(path),
                         'name': path.name,
                         'type': 'dir' if path.is_dir() else 'file'}
            children.append(file_info)

            if path.is_dir():
                continue

            track = Track.by_relpath(conn, music.to_relpath(path))
            if track:
                meta = track.metadata()
                file_info['type'] = 'music'
                file_info['artist'] = ', '.join(meta.artists) if meta.artists else ''
                file_info['title'] = meta.title if meta.title else ''

    # Sort directories first, and ignore case for file name
    def sort_name(obj):
        return ('a' if obj['type'] == 'dir' else 'b') + obj['name'].lower()

    children = sorted(children, key=sort_name)

    return render_template('files.jinja2',
                           base_path=music.to_relpath(browse_path),
                           parent_path=parent_path,
                           write_permission=write_permission,
                           files=children,
                           music_extensions=','.join(music.MUSIC_EXTENSIONS),
                           csrf_token=csrf_token,
                           show_trashed=show_trashed)


@bp.route('/upload', methods=['POST'])
def route_upload():
    """
    Form target to upload file, called from file manager
    """
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        upload_dir = music.from_relpath(request.form['dir'])

        playlist = Playlist.from_path(conn, upload_dir)
        if not playlist.has_write_permission(user):
            abort(403, 'No write permission for this playlist')

    if len(request.files.getlist('upload')) == 0:
        abort(400, 'No files provided.')

    for uploaded_file in request.files.getlist('upload'):
        if uploaded_file.filename is None or uploaded_file.filename == '':
            abort(400, 'Blank file name. Did you select a file?')

        util.check_filename(uploaded_file.filename)
        uploaded_file.save(Path(upload_dir, uploaded_file.filename))

    with db.connect() as conn:
        scanner.scan_tracks(conn, playlist.name)

    return redirect('/files?path=' + urlencode(music.to_relpath(upload_dir)), code=303)


@bp.route('/rename', methods=['GET', 'POST'])
def route_rename():
    """
    Page and form target to rename file
    """
    with db.connect(read_only=request.method == 'GET') as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=request.method == 'POST')

        if request.method == 'POST':
            if request.is_json:
                relpath = request.json['path']
                new_name = request.json['new_name']
            else:
                relpath = request.form['path']
                new_name = request.form['new-name']

            path = music.from_relpath(relpath)
            util.check_filename(new_name)

            playlist = Playlist.from_path(conn, path)
            if not playlist.has_write_permission(user):
                abort(403, 'No write permission for this playlist')

            path.rename(Path(path.parent, new_name))

            # TODO use scanner.scan_track to only scan the two changed tracks
            scanner.scan_tracks(conn, playlist.name)

            if request.is_json:
                return Response(None, 200)

            return redirect('/files?path=' + urlencode(music.to_relpath(path.parent)), code=303)
        else:
            path = music.from_relpath(request.args['path'])
            back_url = request.args['back_url']
            return render_template('files_rename.jinja2',
                                csrf_token=user.get_csrf(),
                                path=music.to_relpath(path),
                                name=path.name,
                                back_url=back_url)


@bp.route('/mkdir', methods=['POST'])
def route_mkdir():
    """
    Create directory, then enter it
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

    path = music.from_relpath(request.form['path'])

    playlist = Playlist.from_path(conn, path)
    if not playlist.has_write_permission(user):
        abort(403, 'No write permission for this playlist')

    dirname = request.form['dirname']
    util.check_filename(dirname)
    Path(path, dirname).mkdir()
    return redirect('/files?path=' + urlencode(music.to_relpath(path)), code=303)


@bp.route('/download')
def route_download():
    """
    Download single file
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    path = music.from_relpath(request.args['path'])
    return send_file(path, as_attachment=True)


@bp.route('/download_zip')
def route_download_zip():
    """
    Download directory as zip file
    """
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)
    path = music.from_relpath(request.args['path'])
    return send_directory(path)

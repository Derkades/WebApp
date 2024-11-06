import difflib
import re
from unicodedata import normalize
from flask import (Blueprint, Response, abort, redirect, render_template,
                   request)


from raphson_mp import auth, db, jsonw, music, scanner, settings, spotify, util
from raphson_mp import metadata
from raphson_mp.metadata import Metadata, normalize_title

bp = Blueprint('playlists', __name__, url_prefix='/playlist')


@bp.route('/manage')
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

    spotify_available = settings.spotify_api_id and settings.spotify_api_secret

    return render_template('playlists.jinja2',
                           user_is_admin=user.admin,
                           playlists=user_playlists,
                           csrf_token=csrf_token,
                           primary_playlist=primary_playlist,
                           playlists_stats=playlists_stats,
                           spotify_available=spotify_available)


@bp.route('/favorite', methods=['POST'])
def route_favorite():
    """
    Form target to mark a playlist as favorite.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        playlist = request.form['playlist']
        is_favorite = request.form['favorite']
        if is_favorite == '1':
            conn.execute('INSERT INTO user_playlist_favorite VALUES (?, ?) ON CONFLICT DO NOTHING',
                         (user.user_id, playlist))
        else:
            conn.execute('DELETE FROM user_playlist_favorite WHERE user=? AND playlist=?',
                         (user.user_id, playlist))

    return redirect('/playlist/manage', code=303)


@bp.route('/set_primary', methods=['POST'])
def route_set_primary():
    """
    Form target to configure a primary playlist.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        playlist = request.form['primary-playlist']
        conn.execute('UPDATE user SET primary_playlist=? WHERE id=?',
                     (playlist, user.user_id))

    return redirect('/playlist/manage', code=303)


@bp.route('/create', methods=['POST'])
def route_create():
    """
    Form target to create playlist, called from /playlist/manage page
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        name = request.form['name']

        util.check_filename(name)

        path = settings.music_dir / name

        if path.exists():
            abort(400, 'Playlist path already exists')

        path.mkdir()

    # Database connection must be closed because scanner creates its own connection
    scanner.scan()  # This creates a row for the playlist in the playlist table

    with db.connect() as conn:
        # New playlist should be writable for user who created it
        conn.execute('INSERT INTO user_playlist_write VALUES (?, ?)',
                     (user.user_id, name))

    return redirect('/playlist/manage', code=303)


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
        user = auth.verify_auth_cookie(conn, require_csrf=True)
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

        return redirect('/playlist/manage', code=303)


@bp.route('/list')
def route_list():
    with db.connect(read_only=True) as conn:
        user = auth.verify_auth_cookie(conn)

        user_playlists = music.user_playlists(conn, user.user_id, all_writable=user.admin)
        json = [{'name': playlist.name,
                 'track_count': playlist.track_count,
                 'favorite': playlist.favorite,
                 'write': playlist.write}
                for playlist in user_playlists
                if playlist.track_count > 0]
        response = jsonw.json_response(json)
        response.cache_control.max_age = 60;
        return response


@bp.route('/<playlist>/choose_track', methods=['POST'])
def route_track(playlist):
    """
    Choose random track from the provided playlist directory.
    """
    with db.connect() as conn:
        user = auth.verify_auth_cookie(conn, require_csrf=True)

        playlist_obj = music.playlist(conn, playlist)
        require_metadata: bool = request.json['require_metadata'] if 'require_metadata' in request.json else False
        if 'tag_mode' in request.json:
            tag_mode = request.json['tag_mode']
            assert tag_mode in {'allow', 'deny'}
            tags = request.json['tags']
            assert isinstance(tags, list)
            chosen_track = playlist_obj.choose_track(user, require_metadata=require_metadata, tag_mode=tag_mode, tags=tags)
        else:
            chosen_track = playlist_obj.choose_track(user, require_metadata=require_metadata)

        if chosen_track is None:
            return Response('no track found', 404, content_type='text/plain')

        return chosen_track.info_dict()


@bp.route('/<playlist_name>/compare_spotify')
def route_compare_spotify(playlist_name: str):
    with db.connect(read_only=True) as conn:
        auth.verify_auth_cookie(conn)

        local_tracks: dict[tuple[str, tuple[str]], tuple[str, list[str]]] = {}

        for title, artists in conn.execute("""
                                           SELECT title, GROUP_CONCAT(artist, ';') AS artists
                                           FROM track JOIN track_artist ON track.path = track_artist.track
                                           WHERE track.playlist = ?
                                           GROUP BY track.path
                                           """, (playlist_name,)):
            local_track = (title, artists.split(';'))
            key = (normalize_title(title), tuple(local_track[1]))
            local_tracks[key] = local_track

        client = spotify.SpotifyClient()
        spotify_tracks = client.get_playlist(request.args['playlist_id'])

        duplicate_check: set[str] = set()
        duplicates: list[spotify.SpotifyTrack] = []
        both: list[tuple[tuple[str, list[str]], spotify.SpotifyTrack]] = []
        only_spotify: list[spotify.SpotifyTrack] = []
        only_local: list[tuple[str, list[str]]] = []

        for spotify_track in spotify_tracks:
            normalized_title = metadata.normalize_title(spotify_track.title)

            # Spotify duplicates
            duplicate_check_entry = spotify_track.display
            if duplicate_check_entry in duplicate_check:
                duplicates.append(spotify_track)
            duplicate_check.add(duplicate_check_entry)

            # Try to find fast exact match
            local_track_key = (normalized_title, tuple(spotify_track.artists))
            if local_track_key in local_tracks:
                local_track = local_tracks[local_track_key]
            else:
                # Cannot find exact match, look for partial match
                for local_track_key, local_track in local_tracks.items():
                    (local_track_normalized_title, local_track_artists) = local_track_key
                    if difflib.SequenceMatcher(None, normalized_title, local_track_normalized_title).ratio() > 0.8:
                        # Title matches, now check if artist matches (more expensive)

                        artist_match = False
                        for artist_a in spotify_track.artists:
                            for artist_b in local_track_artists:
                                if difflib.SequenceMatcher(None, artist_a.lower(), artist_b.lower()).ratio() > 0.8:
                                    artist_match = True
                                    break

                        if artist_match:
                            break
                else:
                    # no match found
                    only_spotify.append(spotify_track)
                    continue

            # match found, present in both
            del local_tracks[local_track_key]
            both.append((local_track, spotify_track))

        # any local tracks still left in the dict must have no matching spotify track
        only_local.extend(local_tracks.values())

    return render_template('spotify_compare.jinja2',
                           duplicates=duplicates,
                           both=both,
                           only_local=only_local,
                           only_spotify=only_spotify)

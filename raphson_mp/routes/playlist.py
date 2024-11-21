from queue import Queue
from sqlite3 import Connection
from threading import Thread
from typing import cast

from flask import (Blueprint, abort, redirect, render_template,
                   request)

from raphson_mp import (db, jsonw, metadata, music, scanner, settings,
                        spotify, util)
from raphson_mp.auth import User
from raphson_mp.decorators import route
from raphson_mp.metadata import normalize_title
from raphson_mp.spotify import SpotifyTrack
from raphson_mp.music import TagMode

bp = Blueprint('playlists', __name__, url_prefix='/playlist')


# TODO change URL to simply /playlists instead of /playlists/manage
@route(bp, '/manage')
def route_playlists(conn: Connection, user: User):
    """
    Playlist management page
    """
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
                           primary_playlist=primary_playlist,
                           playlists_stats=playlists_stats,
                           spotify_available=spotify_available)


@route(bp, '/favorite', methods=['POST'], write=True)
def route_favorite(conn: Connection, user: User):
    """
    Form target to mark a playlist as favorite.
    """
    playlist = request.form['playlist']
    is_favorite = request.form['favorite']
    if is_favorite == '1':
        conn.execute('INSERT INTO user_playlist_favorite VALUES (?, ?) ON CONFLICT DO NOTHING',
                        (user.user_id, playlist))
    else:
        conn.execute('DELETE FROM user_playlist_favorite WHERE user=? AND playlist=?',
                        (user.user_id, playlist))

    return redirect('/playlist/manage', code=303)


@route(bp, '/create', methods=['POST'], write=True)
def route_create(conn: Connection, user: User):
    """
    Form target to create playlist, called from /playlist/manage page
    """
    name = request.form['name']

    util.check_filename(name)

    path = settings.music_dir / name

    if path.exists():
        abort(400, 'Playlist path already exists')

    path.mkdir()

    scanner.scan_playlists(conn)  # This creates a row for the playlist in the playlist table

    # New playlist should be writable for user who created it
    conn.execute('INSERT INTO user_playlist_write VALUES (?, ?)',
                    (user.user_id, name))

    return redirect('/playlist/manage', code=303)


@route(bp, '/share', methods=['GET', 'POST'], write=True)
def route_share(conn: Connection, user: User):
    """
    GET: Page to select a username to share the provided playlist with
    POST: Form target to submit the selected username
    """
    if request.method == 'GET':
        usernames = [row[0] for row in conn.execute('SELECT username FROM user')]
        csrf = request.args['csrf']
        playlist_relpath = request.args['playlist']
        return render_template('playlists_share.jinja2',
                               csrf=csrf,
                               playlist=playlist_relpath,
                               usernames=usernames)

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


@route(bp, '/list')
def route_list(conn: Connection, user: User):
    user_playlists = music.user_playlists(conn, user.user_id, all_writable=user.admin)
    json = [{'name': playlist.name,
                'track_count': playlist.track_count,
                'favorite': playlist.favorite,
                'write': playlist.write}
            for playlist in user_playlists
            if playlist.track_count > 0]
    response = jsonw.json_response(json)
    response.cache_control.max_age = 60
    return response


@route(bp, '/<playlist_name>/choose_track', methods=['POST'], write=True)
def route_track(conn: Connection, user: User, playlist_name: str):
    """
    Choose random track from the provided playlist directory.
    """
    playlist = music.playlist(conn, playlist_name)
    require_metadata: bool = cast(bool, request.json['require_metadata']) if 'require_metadata' in request.json else False
    if 'tag_mode' in request.json:
        tag_mode = TagMode.from_value(cast(str, request.json['tag_mode']))
        tags = cast(list[str], request.json['tags'])
        chosen_track = playlist.choose_track(user, require_metadata=require_metadata, tag_mode=tag_mode, tags=tags)
    else:
        chosen_track = playlist.choose_track(user, require_metadata=require_metadata)

    if chosen_track is None:
        abort(404, 'no track found')

    return chosen_track.info_dict()


def _fuzzy_match_track(spotify_normalized_title: str, local_track_key: tuple[str, tuple[str]], spotify_track: SpotifyTrack) -> bool:
    (local_track_normalized_title, local_track_artists) = local_track_key
    if not util.str_match(spotify_normalized_title, local_track_normalized_title):
        return False

    # Title matches, now check if artist matches (more expensive)
    for artist_a in spotify_track.artists:
        for artist_b in local_track_artists:
            if util.str_match(artist_a, artist_b):
                return True

    return False


@route(bp, '/<playlist_name>/compare_spotify')
def route_compare_spotify(conn: Connection, _user: User, playlist_name: str):
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

    playlist_id = request.args['playlist_id']
    spotify_tracks: Queue[SpotifyTrack|object] = Queue(maxsize=200)
    sentinel = object()

    # Retrieve track list from Spotify in a separate thread
    def get_tracks():
        try:
            client = spotify.SpotifyClient()
            for track in client.get_playlist(playlist_id):
                spotify_tracks.put(track)
        finally:
            spotify_tracks.put(sentinel)
    Thread(target=get_tracks).start()

    duplicate_check: set[str] = set()
    duplicates: list[SpotifyTrack] = []
    both: list[tuple[tuple[str, list[str]], SpotifyTrack]] = []
    only_spotify: list[SpotifyTrack] = []
    only_local: list[tuple[str, list[str]]] = []

    for spotify_track in iter(spotify_tracks.get, sentinel):
        spotify_track = cast(SpotifyTrack, spotify_track)
        spotify_tracks.task_done()

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
            for local_track_key in local_tracks.keys():
                if _fuzzy_match_track(normalized_title, local_track_key, spotify_track):
                    break
            else:
                # no match found
                only_spotify.append(spotify_track)
                continue

        # match found, present in both
        both.append((local_tracks[local_track_key], spotify_track))
        del local_tracks[local_track_key]

    # any local tracks still left in the dict must have no matching spotify track
    only_local.extend(local_tracks.values())

    return render_template('spotify_compare.jinja2',
                           duplicates=duplicates,
                           both=both,
                           only_local=only_local,
                           only_spotify=only_spotify)

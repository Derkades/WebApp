# pylint: disable=import-outside-toplevel

import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from raphson_mp import auth, logconfig, settings

log = logging.getLogger(__name__)


def handle_start(args: Any, logconfig_dict: dict) -> None:
    """
    Handle command to start server
    """
    from raphson_mp import cleanup, db
    from raphson_mp import main as app_main
    from raphson_mp import scanner

    if os.getenv('WERKZEUG_RUN_MAIN') != 'true':  # skip if reloading
        db.migrate()
        scanner.scan()
        cleanup.cleanup()

    if args.dev:
        log.info('Starting Flask web server in debug mode')
        app = app_main.get_app(args.proxy_count, True)
        app.run(host=args.host, port=args.port, debug=True)
        return

    from raphson_mp import gunicorn_app

    log.info('Starting gunicorn web server')
    bind = f'[{args.host}]:{args.port}'
    gapp = gunicorn_app.GunicornApp(bind, args.proxy_count, logconfig_dict)
    gapp.run()


def handle_useradd(args: Any) -> None:
    """
    Handle command to add user
    """
    from raphson_mp import db

    username = args.username
    is_admin = int(args.admin)
    password = input('Enter password:')

    hashed_password = auth.hash_password(password)

    with db.connect() as conn:
        conn.execute('INSERT INTO user (username, password, admin) VALUES (?, ?, ?)',
                     (username, hashed_password, is_admin,))

    log.info('User added successfully')


def handle_userdel(args: Any) -> None:
    """
    Handle command to delete user
    """
    from raphson_mp import db

    with db.connect() as conn:
        deleted = conn.execute('DELETE FROM user WHERE username=?',
                               (args.username,)).rowcount
        if deleted == 0:
            log.warning('No user deleted, does the user exist?')
        else:
            log.info('User deleted successfully')


def handle_userlist(_args: Any) -> None:
    """
    Handle command to list users
    """
    from raphson_mp import db

    with db.connect() as conn:
        result = conn.execute('SELECT username, admin FROM user')
        if result.rowcount == 0:
            log.info('No users')
            return

        log.info('Users:')

        for username, is_admin in result:
            if is_admin:
                log.info('- %s (admin)', username)
            else:
                log.info('- %s', username)


def handle_passwd(args: Any) -> None:
    """
    Handle command to change a user's password
    """
    from raphson_mp import db, util

    with db.connect() as conn:
        result = conn.execute('SELECT id FROM user WHERE username=?',
                              (args.username,)).fetchone()
        if result is None:
            print('No user exists with the provided username')
            return

        user_id = result[0]

        password = input('Enter new password:')
        hashed_password = auth.hash_password(password)

        conn.execute('UPDATE user SET password=? WHERE id=?', (hashed_password, user_id))

        print('Password updated successfully.')


def handle_playlist(args: Any) -> None:
    """
    Handle command to give a user write access to a playlist
    """
    from raphson_mp import db

    with db.connect() as conn:
        result = conn.execute('SELECT id FROM user WHERE username=?',
                              (args.username,)).fetchone()
        if result is None:
            print('No user exists with the provided username')
            return

        user_id = result[0]

        result = conn.execute('SELECT path FROM playlist WHERE path=?',
                              (args.playlist_path,)).fetchone()

        if result is None:
            print('Playlist does not exist. If you just added it, please re-scan first.')
            return

        playlist = result[0]

        conn.execute('INSERT INTO user_playlist_write VALUES (?, ?) ON CONFLICT DO NOTHING',
                     (user_id, playlist))

        log.info('Given user %s access to playlist %s', args.username, args.playlist_path)


def handle_scan(_args: Any) -> None:
    """
    Handle command to scan playlists
    """
    from raphson_mp import scanner

    scanner.scan()


def handle_cleanup(_args: Any) -> None:
    """
    Handle command to clean up old entries from databases
    """
    from raphson_mp import cleanup

    cleanup.cleanup()


def handle_migrate(_args: Any) -> None:
    """
    Handle command for database migration
    """
    from raphson_mp import db
    db.migrate()


def handle_vacuum(_args: Any) -> None:
    """
    Handle command for database vacuuming
    """
    from raphson_mp import db
    log.info('Going to vacuum databases. This will take a long time if you have large databases. Do not abort.')

    log.info('Vacuuming music.db')
    with db.connect() as conn:
        conn.execute('VACUUM')

    log.info('Vacuuming cache.db')
    with db.cache() as conn:
        conn.execute('VACUUM')

    log.info('Vacuuming offline.db')
    with db.offline() as conn:
        conn.execute('VACUUM')


def handle_sync(args: Any) -> None:
    """
    Handle command for offline mode sync
    """
    from raphson_mp import offline_sync

    if args.playlists is not None:
        if args.playlists == 'favorite':
            offline_sync.change_playlists([])
            return

        playlists = args.playlists.split(',')
        offline_sync.change_playlists(playlists)
        return

    offline_sync.do_sync(args.force_resync)


def handle_cover(args: Any) -> None:
    from raphson_mp import music

    cover_bytes = next(music._get_possible_covers(args.artist, args.title, args.meme))
    Path('cover.jpg').write_bytes(cover_bytes)


def handle_acoustid(args: Any) -> None:
    from raphson_mp import acoustid, musicbrainz

    fp = acoustid.get_fingerprint(Path(args.path))
    log.info('duration: %s', fp.duration)
    log.info('fingerprint: %s', fp.fingerprint_b64)

    recordings = acoustid.lookup(fp)

    for recording in recordings[:2]:
        for meta in musicbrainz.get_recording_metadata(recording):
            log.info('possible metadata for recording %s: %s', recording, meta)


def handle_lyrics(args: Any) -> None:
    from raphson_mp.lyrics import PlainLyrics, TimeSyncedLyrics, find

    lyrics = find(args.title, args.artist, args.album, args.duration)

    if isinstance(lyrics, PlainLyrics):
        print(lyrics.text)
    elif isinstance(lyrics, TimeSyncedLyrics):
        print(lyrics.to_lrc())
    elif lyrics is None:
        print('No lyrics found')
        sys.exit(1)
    else:
        raise ValueError(lyrics)


def handle_bing(args: Any) -> None:
    from raphson_mp import bing

    results = bing.image_search(args.query)
    Path('bing_result').write_bytes(next(results))
    log.info('saved to bing_result file')


def _strenv(name: str, default: str | None = None) -> str | None:
    return os.getenv('MUSIC_' + name, default)


def _intenv(name: str, default: int) -> int | None:
    text = _strenv(name, str(default))
    if text is None:
        return None
    return int(text)


def _boolenv(name: str) -> bool:
    val = _strenv(name, '')
    return val == '1' or bool(val)


def split_by_comma(inp: str | None) -> list[str]:
    if inp is None:
        return []
    return [s.strip() for s in inp.split(',') if s.strip() != '']


def main():
    parser = ArgumentParser()
    parser.add_argument('--log-level',
                        default=_strenv('LOG_LEVEL', 'INFO'),
                        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
                        help='set log level for Python loggers')
    parser.add_argument('--short-log-format',
                        action='store_true',
                        default=_boolenv('SHORT_LOG_FORMAT'),
                        help='use short log format')
    parser.add_argument('--data-dir',
                        default=_strenv('DATA_DIR', _strenv('DATA_PATH', './data')),
                        help='path to directory where program data is stored')
    parser.add_argument('--music-dir',
                        default=_strenv('MUSIC_DIR', './music'),
                        help='path to directory where music files are stored')
    # error level by default to hide unfixable "deprecated pixel format used" warning
    parser.add_argument('--ffmpeg-log-level', default=_strenv('FFMPEG_LOG_LEVEL', 'error'),
                        choices=('quiet', 'fatal', 'error', 'warning', 'info', 'verbose', 'debug'),
                        help='log level for ffmpeg')
    parser.add_argument('--track-max-duration-seconds',
                        type=int,
                        default=_intenv('TRACK_MAX_DURATION_SECONDS', 1200))
    parser.add_argument('--radio-playlists',
                        default=_strenv('RADIO_PLAYLISTS'),
                        help='comma-separated list of playlists to use for radio')
    parser.add_argument('--lastfm-api-key',
                        default=_strenv('LASTFM_API_KEY'))
    parser.add_argument('--lastfm-api-secret',
                        default=_strenv('LASTFM_API_SECRET'))
    parser.add_argument('--offline',
                        action='store_true',
                        default=_boolenv('OFFLINE_MODE'),
                        help='run in offline mode, using music synced from a primary music server')
    parser.add_argument('--news-server',
                        help='news server url: https://github.com/Derkades/news-scraper',
                        default=_strenv('NEWS_SERVER', 'http://127.0.0.1:43473'))

    subparsers = parser.add_subparsers(required=True)

    cmd_start = subparsers.add_parser('start', help='start app in debug mode')
    cmd_start.add_argument('--host', default='127.0.0.1', type=str)
    cmd_start.add_argument('--port', default=8080, type=int)
    cmd_start.add_argument('--dev', action='store_true')
    cmd_start.add_argument('--proxy-count', type=int, default=_intenv('PROXY_COUNT', _intenv('PROXIES_X_FORWARDED_FOR', 0)))
    cmd_start.set_defaults(func=handle_start)

    cmd_useradd = subparsers.add_parser('useradd', help='create new user')
    cmd_useradd.add_argument('username')
    cmd_useradd.add_argument('--admin', action='store_true',
                             help='created user should have administrative rights')
    cmd_useradd.set_defaults(func=handle_useradd)

    cmd_userdel = subparsers.add_parser('userdel',
                                        help='delete a user')
    cmd_userdel.add_argument('username')
    cmd_userdel.set_defaults(func=handle_userdel)

    cmd_userlist = subparsers.add_parser('userlist',
                                         help='list users')
    cmd_userlist.set_defaults(func=handle_userlist)

    cmd_passwd = subparsers.add_parser('passwd',
                                       help='change password')
    cmd_passwd.add_argument('username')
    cmd_passwd.set_defaults(func=handle_passwd)

    cmd_playlist = subparsers.add_parser('playlist',
                                         help='give write access to playlist')
    cmd_playlist.add_argument('username')
    cmd_playlist.add_argument('playlist_path')
    cmd_playlist.set_defaults(func=handle_playlist)

    cmd_scan = subparsers.add_parser('scan',
                                     help='scan playlists for changes')
    cmd_scan.set_defaults(func=handle_scan)

    cmd_cleanup = subparsers.add_parser('cleanup',
                                        help='clean old or unused data from the database')
    cmd_cleanup.set_defaults(func=handle_cleanup)

    cmd_migrate = subparsers.add_parser('migrate',
                                       help='run database migrations')
    cmd_migrate.set_defaults(func=handle_migrate)

    cmd_vacuum = subparsers.add_parser('vacuum',
                                       help='issue vacuum command to clean up sqlite databases')
    cmd_vacuum.set_defaults(func=handle_vacuum)

    cmd_sync = subparsers.add_parser('sync',
                                     help='sync tracks from main server (offline mode)')
    cmd_sync.add_argument('--force-resync', type=float, default=0.0,
                          help='Ratio of randomly selected tracks to redownload even if up to date')
    cmd_sync.add_argument('--playlists', type=str,
                          help='Change playlists to sync. Specify playlists as comma separated list without spaces. Enter \'favorite\' to sync favorite playlists (default).')
    cmd_sync.set_defaults(func=handle_sync)

    cmd_cover = subparsers.add_parser('debug-cover',
                                      help='Download cover image')
    cmd_cover.add_argument('artist')
    cmd_cover.add_argument('title')
    cmd_cover.add_argument('--meme', action='store_true')
    cmd_cover.set_defaults(func=handle_cover)

    cmd_cover = subparsers.add_parser('debug-acoustid')
    cmd_cover.add_argument('path')
    cmd_cover.set_defaults(func=handle_acoustid)

    cmd_cover = subparsers.add_parser('debug-lyrics')
    cmd_cover.add_argument('--title', required=True)
    cmd_cover.add_argument('--artist', required=True)
    cmd_cover.add_argument('--album')
    cmd_cover.add_argument('--duration', type=int)
    cmd_cover.set_defaults(func=handle_lyrics)

    cmd_cover = subparsers.add_parser('debug-bing')
    cmd_cover.add_argument('query')
    cmd_cover.set_defaults(func=handle_bing)

    args = parser.parse_args()

    settings.data_dir = Path(args.data_dir).absolute()
    assert settings.data_dir.exists(), 'data dir does not exist: ' + settings.data_dir.as_posix()
    settings.ffmpeg_log_level = args.ffmpeg_log_level
    settings.track_max_duration_seconds = args.track_max_duration_seconds
    settings.radio_playlists = split_by_comma(args.radio_playlists)
    settings.lastfm_api_key = args.lastfm_api_key
    settings.lastfm_api_secret = args.lastfm_api_secret
    settings.offline_mode = args.offline
    settings.news_server = args.news_server

    if settings.offline_mode:
        settings.music_dir = Path('/dev/null')
    else:
        assert args.music_dir, 'music dir must be set when not running in offline mode'
        settings.music_dir = Path(args.music_dir).resolve()
        assert settings.music_dir.exists(), 'music dir does not exist: ' + settings.music_dir.as_posix()

    logconfig_dict = logconfig.get_config_dict(args.short_log_format, Path(args.data_dir, 'errors.log'), args.log_level)
    logconfig.apply(logconfig_dict)

    log.info('music=%s data=%s', settings.music_dir.as_posix(), settings.data_dir.as_posix())

    if args.func == handle_start:
        handle_start(args, logconfig_dict)
    else:
        args.func(args)


if __name__ == '__main__':
    main()

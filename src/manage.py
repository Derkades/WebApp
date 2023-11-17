"""
Management command
"""
import logging
# pylint: disable=import-outside-toplevel
from argparse import ArgumentParser
from typing import Any

import db
import util

log = logging.getLogger('app.manage')


def handle_useradd(args: Any) -> None:
    """
    Handle command to add user
    """
    username = args.username
    is_admin = int(args.admin)
    password = input('Enter password:')

    hashed_password = util.hash_password(password)

    with db.connect() as conn:
        conn.execute('INSERT INTO user (username, password, admin) VALUES (?, ?, ?)',
                     (username, hashed_password, is_admin,))

    log.info('User added successfully')


def handle_userdel(args: Any) -> None:
    """
    Handle command to delete user
    """
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
    with db.connect() as conn:
        result = conn.execute('SELECT id FROM user WHERE username=?',
                              (args.username,)).fetchone()
        if result is None:
            print('No user exists with the provided username')
            return

        user_id = result[0]

        password = input('Enter new password:')
        hashed_password = util.hash_password(password)

        conn.execute('UPDATE user SET password=? WHERE id=?', (hashed_password, user_id))

        print('Password updated successfully.')


def handle_playlist(args: Any) -> None:
    """
    Handle command to give a user write access to a playlist
    """
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
    import scanner

    with db.connect() as conn:
        scanner.scan(conn)


def handle_cleanup(_args: Any) -> None:
    """
    Handle command to clean up old entries from databases
    """
    import cleanup

    cleanup.cleanup()


def handle_vacuum(_args: Any) -> None:
    """
    Handle command for database vacuuming
    """
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


def handle_sync(_args: Any) -> None:
    """
    Handle command for offline mode sync
    """
    import offline_sync
    offline_sync.do_sync()


if __name__ == '__main__':
    import logconfig
    logconfig.apply()

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

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

    cmd_vacuum = subparsers.add_parser('vacuum',
                                       help='issue vacuum command to clean up sqlite databases')
    cmd_vacuum.set_defaults(func=handle_vacuum)

    cmd_sync = subparsers.add_parser('sync',
                                     help='sync tracks from main server (offline mode)')
    cmd_sync.set_defaults(func=handle_sync)

    parsed_args = parser.parse_args()
    parsed_args.func(parsed_args)

from argparse import ArgumentParser
import logging
import time

import db


log = logging.getLogger('app.manage')


def handle_useradd(args):
    """
    Handle command to add user
    """
    import bcrypt
    username = args.username
    is_admin = int(args.admin)
    password = input('Enter password:')

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    with db.connect() as conn:
        conn.execute('INSERT INTO user (username, password, admin) VALUES (?, ?, ?)',
                     (username, hashed_password, is_admin,))

    log.info('User added successfully')


def handle_userdel(args):
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


def handle_userlist(args):
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


def handle_passwd(args):
    """
    Handle command to change a user's password
    """
    import bcrypt

    with db.connect() as conn:
        result = conn.execute('SELECT id FROM user WHERE username=?',
                              (args.username,)).fetchone()
        if result is None:
            print('No user exists with the provided username')
            return

        user_id = result[0]

        password = input('Enter new password:')
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        conn.execute('UPDATE user SET password=? WHERE id=?', (hashed_password, user_id))

        print('Password updated successfully.')


def handle_playlist(args):
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

        conn.execute('''
                     INSERT INTO user_playlist (user, playlist, write) VALUES (?, ?, 1)
                     ON CONFLICT (user, playlist) DO UPDATE SET write=1
                     ''',
                     (user_id, result[0]))

        log.info('Given user %s access to playlist %s', args.username, args.playlist_path)


def handle_scan(args):
    """
    Handle command to scan playlists
    """
    import scanner

    with db.connect() as conn:
        scanner.scan(conn)


def handle_cleanup(args):
    import cleanup

    cleanup.cleanup()


if __name__ == '__main__':
    import logconfig
    logconfig.apply()

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    useradd = subparsers.add_parser('useradd', help='create new user')
    useradd.add_argument('username')
    useradd.add_argument('--admin', action='store_true', help='created user should have administrative rights')
    useradd.set_defaults(func=handle_useradd)

    userdel = subparsers.add_parser('userdel', help='delete a user')
    userdel.add_argument('username')
    userdel.set_defaults(func=handle_userdel)

    userlist = subparsers.add_parser('userlist', help='list users')
    userlist.set_defaults(func=handle_userlist)

    passwd = subparsers.add_parser('passwd', help='change password')
    passwd.add_argument('username')
    passwd.set_defaults(func=handle_passwd)

    playlist = subparsers.add_parser('playlist', help='give write access to playlist')
    playlist.add_argument('username')
    playlist.add_argument('playlist_path')
    playlist.set_defaults(func=handle_playlist)

    scan = subparsers.add_parser('scan', help='scan playlists for changes')
    scan.set_defaults(func=handle_scan)

    cleanup = subparsers.add_parser('cleanup', help='clean old or unused data from the database')
    cleanup.set_defaults(func=handle_cleanup)

    args = parser.parse_args()
    args.func(args)

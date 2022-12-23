from argparse import ArgumentParser
import logging

import logconfig
import db
import bcrypt


log = logging.getLogger('app.manage')


def handle_useradd(args):
    username = args.username
    is_admin = int(args.admin)
    password = input('Enter password:')

    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    with db.users() as conn:
        conn.execute('INSERT INTO user (username, password, admin) VALUES (?, ?, ?)',
                     (username, hashed_password, is_admin,))

    log.info('User added successfully')


def handle_userdel(args):
    with db.users() as conn:
        deleted = conn.execute('DELETE FROM user WHERE username=?', (args.username,)).rowcount
        if deleted == 0:
            log.warning('No user deleted, does the user exist?')
        else:
            log.info('User deleted successfully')


def handle_userlist(args):
    with db.users() as conn:
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
    with db.users() as conn:
        result = conn.execute('SELECT id FROM user WHERE username=?', (args.username,)).fetchone()
        if result is None:
            print('No user exists with the provided username')
            return

        user_id = result[0]

        password = password = input('Enter new password:')
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        conn.execute('UPDATE user SET password=? WHERE id=?', (hashed_password, user_id))

        print('Password updated successfully.')


if __name__ == '__main__':
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

    args = parser.parse_args()
    args.func(args)

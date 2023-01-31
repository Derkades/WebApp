import os
import base64
import logging
import sqlite3
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum, unique
from sqlite3 import Connection

import bcrypt
from flask import request
from flask_babel import _


log = logging.getLogger('app.auth')


@dataclass
class Session:
    rowid: int
    token: str
    creation_timestamp: int
    user_agent: Optional[str]
    remote_address: Optional[str]

    @property
    def creation_date(self) -> str:
        minutes_ago = (int(time.time()) - self.creation_timestamp) // 60
        if minutes_ago == 0:
            return _('Just now')
        if minutes_ago == 1:
            return _('1 minute ago')
        if minutes_ago < 120:
            return _('%(minutes)d minutes ago', minutes=minutes_ago)

        hours_ago = minutes_ago // 60
        if hours_ago == 1:
            return _('1 hour ago')
        if hours_ago < 48:
            return _('%(hours)d hours ago', hours=hours_ago)

        days_ago = hours_ago // 24
        if days_ago == 1:
            return _('1 day ago')

        return _('%(days)d days ago', days=days_ago)

    @property
    def last_device(self) -> Optional[str]:
        """
        Last device string, based on user agent string
        """
        if self.user_agent is None:
            return _('Unknown')

        browsers = ['Firefox', 'Chromium', 'Chrome', 'Vivaldi', 'Opera', 'Safari']
        systems = ['Windows', 'macOS', 'Android', 'iOS', 'Linux']

        for maybe_browser in browsers:
            if maybe_browser in self.user_agent:
                browser = maybe_browser
                break
        else:
            browser = _('Unknown')

        for maybe_system in systems:
            if maybe_system in self.user_agent:
                system = maybe_system
                break
        else:
            system = _('Unknown')

        return f'{browser}, {system}'


@dataclass
class User:
    conn: sqlite3.Connection
    user_id: int
    username: str
    admin: bool
    session: Session
    lastfm_name: Optional[str]
    lastfm_key: Optional[str]

    def sessions(self):
        """
        Get all sessions for users
        """
        results = self.conn.execute("""
                                    SELECT rowid, token, creation_date, user_agent, remote_address
                                    FROM session WHERE user=?
                                    """, (self.user_id,)).fetchall()
        return [Session(*row) for row in results]

    def get_csrf(self) -> str:
        """
        Generate CSRF token and store it for later validation
        """
        token = _generate_token()
        now = int(time.time())
        self.conn.execute('INSERT INTO csrf (user, token, creation_date) VALUES (?, ?, ?)',
                          (self.user_id, token, now))
        return token

    def verify_csrf(self, token: str) -> None:
        """
        Verify request token, raising RequestTokenException if not valid
        """
        week_ago = int(time.time()) - 3600
        result = self.conn.execute('SELECT token FROM session WHERE user=? AND token=? AND creation_date > ?',
                                   (self.user_id, token, week_ago))
        if result is None:
            raise RequestTokenError()

    def verify_password(self, password: str) -> bool:
        """
        Verify password matches user's existing password
        Returns: True if password matches, False if not.
        """
        result = self.conn.execute('SELECT password FROM user WHERE id=?',
                                   (self.user_id,)).fetchone()
        hashed_password, = result
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    def update_password(self, new_password: str) -> None:
        """
        Update user password and delete all existing sessions.
        """
        hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self.conn.execute('UPDATE user SET password=? WHERE id=?',
                          (hashed_password, self.user_id))
        self.conn.execute('DELETE FROM session WHERE user=?',
                          (self.user_id,))


@unique
class AuthErrorReason(Enum):
    NO_TOKEN = 1
    INVALID_TOKEN = 2
    ADMIN_REQUIRED = 3

    @property
    def message(self):
        """
        Get translated message corresponding to auth error reason
        """
        if self is AuthErrorReason.NO_TOKEN:
            return _('You are not logged in, please log in.')
        elif self is AuthErrorReason.INVALID_TOKEN:
            return _('Your current session is invalid, please log in again.')
        elif self is AuthErrorReason.ADMIN_REQUIRED:
            return _('Your are not an administrator, but this page requires administrative privileges')
        else:
            return ValueError()


@dataclass
class AuthError(Exception):
    reason: AuthErrorReason
    redirect: bool


class RequestTokenError(Exception):
    pass


def _generate_token() -> str:
    return base64.b64encode(os.urandom(16)).decode()


def log_in(conn: Connection, username: str, password: str, user_agent: str, remote_addr: str) -> Optional[str]:
    """
    Log in using username and password.
    Args:
        conn: Read-write database connection
        username
        password
        user_agent
        remote_addr
    Returns: Session token, or None if the username+password combination is not valid
    """
    result = conn.execute('SELECT id, password FROM user WHERE username=?', (username,)).fetchone()

    if result is None:
        log.warning("Login attempt with non-existent username: '%s'", username)
        return None

    user_id, hashed_password = result

    if not bcrypt.checkpw(password.encode(), hashed_password.encode()):
        log.warning('Failed login for user %s', username)
        return None

    token = _generate_token()
    creation_date = int(time.time())

    conn.execute('INSERT INTO session (user, token, creation_date, user_agent, remote_address) VALUES (?, ?, ?, ?, ?)',
                    (user_id, token, creation_date, user_agent, remote_addr))

    log.info('Successful login for user %s', username)

    return token


def _verify_token(conn: sqlite3.Connection, token: str) -> Optional[User]:
    """
    Verify session token, and return corresponding user
    Args:
        conn: Read-only database connection
        token: Session token to verify
    Returns: User object if session token is valid, or None if invalid
    """
    # TODO does this introduce the possibility of a timing attack?
    result = conn.execute("""
                          SELECT session.rowid, session.creation_date, session.user_agent, session.remote_address, user.id, user.username, user.admin, user_lastfm.name, user_lastfm.key
                          FROM user
                          INNER JOIN session ON user.id = session.user
                          LEFT JOIN user_lastfm ON user.id = user_lastfm.user
                          WHERE session.token=?
                          """, (token,)).fetchone()
    if result is None:
        log.warning('Invalid auth token: %s', token)
        return None

    session_rowid, session_creation_date, session_user_agent, session_address, user_id, username, admin, lastfm_name, lastfm_key = result

    session = Session(session_rowid, token, session_creation_date, session_user_agent, session_address)
    return User(conn, user_id, username, admin == 1, session, lastfm_name, lastfm_key)


def verify_auth_cookie(conn: sqlite3.Connection, require_admin = False, redirect_to_login = False) -> User:
    """
    Verify auth token sent as cookie, raising AuthError if missing or not valid
    """
    if 'token' not in request.cookies:
        log.warning('No auth token')
        raise AuthError(AuthErrorReason.NO_TOKEN, redirect_to_login)

    token = request.cookies['token']
    user = _verify_token(conn, token)
    if user is None:
        raise AuthError(AuthErrorReason.INVALID_TOKEN, redirect_to_login)

    if require_admin and not user.admin:
        raise AuthError(AuthErrorReason.ADMIN_REQUIRED, redirect_to_login)

    return user

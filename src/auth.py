import os
import base64
import logging
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum, unique
from sqlite3 import Connection, OperationalError
from abc import ABC, abstractmethod

import bcrypt
from flask import request
import flask_babel
from flask_babel import _

import settings


log = logging.getLogger('app.auth')


@dataclass
class Session:
    rowid: int
    token: str
    creation_timestamp: int
    user_agent: Optional[str]
    remote_address: Optional[str]
    last_use: int

    @property
    def creation_date(self) -> str:
        seconds_ago = -(int(time.time()) - self.creation_timestamp)
        return flask_babel.format_timedelta(seconds_ago, add_direction=True)

    @property
    def last_use_ago(self) -> str:
        seconds_ago = -(int(time.time()) - self.last_use)
        return flask_babel.format_timedelta(seconds_ago, add_direction=True)

    @property
    def last_device(self) -> Optional[str]:
        """
        Last device string, based on user agent string
        """
        if self.user_agent is None:
            return _('Unknown')

        if 'Music-Player-Android' in self.user_agent:
            return 'MusicPlayer, Android'

        if self.user_agent == settings.user_agent:
            return 'MusicPlayer'

        browsers = ['Firefox', 'Chromium', 'Chrome', 'Vivaldi', 'Opera', 'Safari']
        systems = ['Windows', 'macOS', 'Android', 'iOS', 'Ubuntu', 'Debian', 'Fedora', 'Linux']

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


class User(ABC):
    user_id: int
    username: str
    admin: bool
    primary_playlist: Optional[str]

    @abstractmethod
    def sessions(self) -> list[Session]:
        """
        Get all sessions for users
        """

    @abstractmethod
    def get_csrf(self) -> str:
        """
        Generate CSRF token and store it for later validation
        """

    def verify_csrf(self, token: str) -> None:
        """
        Verify request token, raising RequestTokenException if not valid
        """

    def verify_password(self, password: str) -> bool:
        """
        Verify password matches user's existing password
        Returns: True if password matches, False if not.
        """

    def update_password(self, new_password: str) -> None:
        """
        Update user password and delete all existing sessions.
        """


@dataclass
class StandardUser(User):
    conn: Connection
    user_id: int
    username: str
    admin: bool
    primary_playlist: Optional[str]

    def sessions(self) -> list[Session]:
        results = self.conn.execute("""
                                    SELECT rowid, token, creation_date, user_agent, remote_address, last_use
                                    FROM session WHERE user=?
                                    """, (self.user_id,)).fetchall()
        return [Session(*row) for row in results]

    def get_csrf(self) -> str:
        token = _generate_token()
        now = int(time.time())
        self.conn.execute('INSERT INTO csrf (user, token, creation_date) VALUES (?, ?, ?)',
                          (self.user_id, token, now))
        return token

    def verify_csrf(self, token: str) -> None:
        min_timestamp = int(time.time()) - settings.csrf_validity_seconds
        result = self.conn.execute('SELECT token FROM csrf WHERE user=? AND token=? AND creation_date > ?',
                                   (self.user_id, token, min_timestamp)).fetchone()
        if result is None:
            raise RequestTokenError()

    def verify_password(self, password: str) -> bool:
        result = self.conn.execute('SELECT password FROM user WHERE id=?',
                                   (self.user_id,)).fetchone()
        hashed_password, = result
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    def update_password(self, new_password: str) -> None:
        hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        self.conn.execute('UPDATE user SET password=? WHERE id=?',
                          (hashed_password, self.user_id))
        self.conn.execute('DELETE FROM session WHERE user=?',
                          (self.user_id,))


class OfflineUser(User):
    def __init__(self):
        self.user_id = 0
        self.username = 'fake offline user'
        self.admin = False
        self.primary_playlist = None

    def sessions(self) -> list[Session]:
        return []

    def get_csrf(self) -> str:
        return 'fake_csrf_token'

    def verify_csrf(self, token: str) -> bool:
        return token == 'fake_csrf_token'

    def verify_password(self, _password: str):
        raise RuntimeError('Password login is not available in offline mode')

    def update_password(self, _new_password: str) -> None:
        raise RuntimeError('Cannot update password in offline mode')


OFFLINE_DUMMY_USER = OfflineUser()


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


def log_in(conn: Connection, username: str, password: str) -> Optional[str]:
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
    if settings.offline_mode:
        raise RuntimeError('Login not available in offline mode')

    result = conn.execute('SELECT id, password FROM user WHERE username=?', (username,)).fetchone()

    if result is None:
        log.warning("Login attempt with non-existent username: '%s'", username)
        return None

    user_id, hashed_password = result

    if not bcrypt.checkpw(password.encode(), hashed_password.encode()):
        log.warning('Failed login for user %s', username)
        return None

    token = _generate_token()
    remote_addr = request.remote_addr
    user_agent = request.headers['User-Agent'] if 'User-Agent' in request.headers else None

    # TODO use unixepoch() after update to debian bookworm
    conn.execute("""
                 INSERT INTO session (user, token, creation_date, user_agent, remote_address, last_use)
                 VALUES (?, ?, strftime('%s', 'now'), ?, ?, strftime('%s', 'now'))
                 """,
                 (user_id, token, user_agent, remote_addr))

    log.info('Successful login for user %s', username)

    return token


def _verify_token(conn: Connection, token: str) -> Optional[User]:
    """
    Verify session token, and return corresponding user
    Args:
        conn: Read-only database connection
        token: Session token to verify
    Returns: User object if session token is valid, or None if invalid
    """
    result = conn.execute("""
                          SELECT session.rowid, user.id, user.username, user.admin, user.primary_playlist
                          FROM user
                              INNER JOIN session ON user.id = session.user
                          WHERE session.token=?
                          """, (token,)).fetchone()
    if result is None:
        log.warning('Invalid auth token: %s', token)
        return None

    session_rowid, user_id, username, admin, primary_playlist = result

    try:
        remote_addr = request.remote_addr
        user_agent = request.headers['User-Agent'] if 'User-Agent' in request.headers else None
        # TODO use unixepoch() after update to debian bookworm
        conn.execute("""
                     UPDATE session
                     SET user_agent=?, remote_address=?, last_use=strftime('%s', 'now')
                     WHERE rowid=?
                     """,
                     (user_agent, remote_addr, session_rowid))
    except OperationalError as ex:
        # Ignore error if database is read-only
        if ex.sqlite_errorname != 'SQLITE_READONLY':
            raise ex

    return StandardUser(conn, user_id, username, admin == 1, primary_playlist)


def verify_auth_cookie(conn: Connection, require_admin = False, redirect_to_login = False) -> User:
    """
    Verify auth token sent as cookie, raising AuthError if missing or not valid.
    Args:
        conn: Read-only database connection
        require_admin: Whether logging in as a non-admin account should be treated as an authentication failure
        redirect_to_login: Whether the user should sent a redirect if authentication failed, instead of showing a 403 page
    """
    if settings.offline_mode:
        return OFFLINE_DUMMY_USER

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


def prune_old_csrf_tokens(conn: Connection) -> int:
    """
    Prune old CSRF tokens
    Args:
        conn: Read-write database connection
    Returns: Number of deleted tokens
    """
    delete_before = int(time.time()) - settings.csrf_validity_seconds
    return conn.execute('DELETE FROM csrf WHERE creation_date < ?',
                        (delete_before,)).rowcount


def prune_old_session_tokens(conn: Connection) -> int:
    """
    Prune old session tokens
    Args:
        conn: Read-write database connection
    Returns: Number of deleted tokens
    """
    one_month_ago = int(time.time()) - 60*60*24*30
    return conn.execute('DELETE FROM session WHERE last_use < ?', (one_month_ago,)).rowcount

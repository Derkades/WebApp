import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, unique
from sqlite3 import Connection, OperationalError
from typing import Optional

import flask_babel
from flask import request
from flask_babel import _

from raphson_mp import jsonw, settings, util

log = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    # https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#scrypt
    salt_bytes = os.urandom(32)
    n = 2**14
    r = 8
    p = 5
    hash_bytes = hashlib.scrypt(password.encode(), salt=salt_bytes, n=n, r=r, p=p)
    hash_json = jsonw.to_json({'alg': 'scrypt',
                               'n': n,
                               'r': r,
                               'p': p,
                               'salt': base64.b64encode(salt_bytes).decode(),
                               'hash': base64.b64encode(hash_bytes).decode()})
    return hash_json


def verify_password(conn: Connection, user_id: int, password: str) -> bool:
    hashed_password, = conn.execute('SELECT password FROM user WHERE id = ?', (user_id,)).fetchone()

    # Upgrade implemented 2024-08-26
    # TODO In a year, remove upgrade code and do not allow users to log in with bcrypt hashed password
    # The server administrator will have to give them a new password
    if hashed_password.startswith('$2b'):
        # Legacy bcrypt password
        log.warning('Upgrading legacy bcrypt password')
        import bcrypt  # only import bcrypt when actually required
        if bcrypt.checkpw(password.encode(), hashed_password.encode()):
            # Password is valid, update to modern hash
            new_hash = hash_password(password)
            conn.execute('UPDATE user SET password = ? WHERE id = ?',  (new_hash, user_id))
            return True
        else:
            return False

    hash_json = jsonw.from_json(hashed_password)
    if hash_json['alg'] == 'scrypt':
        hash_bytes = hashlib.scrypt(password.encode(),
                                    salt=base64.b64decode(hash_json['salt']),
                                    n=hash_json['n'],
                                    r=hash_json['r'],
                                    p=hash_json['p'])
        return hmac.compare_digest(hash_bytes, base64.b64decode(hash_json['hash']))

    raise ValueError('Unknown alg: ' + hash_json['alg'])


@dataclass
class Session:
    rowid: int
    token: str
    csrf_token: str
    creation_timestamp: int
    user_agent: Optional[str]
    remote_address: Optional[str]
    last_use: int

    @property
    def creation_date(self) -> str:
        """
        When session was created, formatted as time ago string
        """
        seconds_ago = self.creation_timestamp - int(time.time())
        return flask_babel.format_timedelta(seconds_ago, add_direction=True)

    @property
    def last_use_ago(self) -> str:
        """
        When account was last used, formatted as time ago string
        """
        seconds_ago = self.last_use - int(time.time())
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

        if self.user_agent == settings.user_agent_offline_sync:
            return 'MusicPlayer offline sync'

        if self.user_agent == 'rmp-playback-server':
            return 'Playback server'

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


class PrivacyOption(Enum):
    NONE = None
    AGGREGATE = 'aggregate'
    HIDDEN = 'hidden'


class User(ABC):
    user_id: int
    username: str
    nickname: str
    admin: bool
    primary_playlist: Optional[str]
    language: Optional[str]
    privacy: PrivacyOption

    @abstractmethod
    def sessions(self) -> list[Session]:
        """
        Get all sessions for users
        """

    @abstractmethod
    def get_csrf(self) -> str:
        """
        Get CSRF token for current session
        """

    @abstractmethod
    def update_password(self, new_password: str) -> None:
        """
        Update user password and delete all existing sessions.
        """


@dataclass
class StandardUser(User):
    conn: Connection
    user_id: int
    username: str
    nickname: str
    admin: bool
    primary_playlist: Optional[str]
    language: Optional[str]
    privacy: PrivacyOption
    session: Session

    def sessions(self) -> list[Session]:
        results = self.conn.execute("""
                                    SELECT rowid, token, csrf_token, creation_date, user_agent, remote_address, last_use
                                    FROM session WHERE user=?
                                    """, (self.user_id,)).fetchall()
        return [Session(*row) for row in results]

    def get_csrf(self) -> str:
        return self.session.csrf_token

    def update_password(self, new_password: str) -> None:
        password_hash = hash_password(new_password)
        self.conn.execute('UPDATE user SET password=? WHERE id=?',
                          (password_hash, self.user_id))
        self.conn.execute('DELETE FROM session WHERE user=?',
                          (self.user_id,))


class OfflineUser(User):
    def __init__(self) -> None:
        self.user_id = 0
        self.username = 'fake_offline_user'
        self.nickname = 'Fake offline user'
        self.admin = False
        self.primary_playlist = None
        self.language = None
        self.privacy = PrivacyOption.NONE

    def sessions(self) -> list[Session]:
        return []

    def get_csrf(self) -> str:
        return 'fake_csrf_token'

    def update_password(self, _new_password: str) -> None:
        raise RuntimeError('Cannot update password in offline mode')


OFFLINE_DUMMY_USER = OfflineUser()


@unique
class AuthErrorReason(Enum):
    NO_TOKEN = 1
    INVALID_TOKEN = 2
    ADMIN_REQUIRED = 3
    MISSING_CSRF = 4
    INVALID_CSRF = 5

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
        elif self is AuthErrorReason.MISSING_CSRF:
            return _('Missing CSRF token from request.')
        elif self is AuthErrorReason.INVALID_TOKEN:
            return _('Invalid CSRF token in request. Please refresh the page and try again.')

        return ValueError()


@dataclass
class AuthError(Exception):
    reason: AuthErrorReason
    redirect: bool


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

    if not verify_password(conn, user_id, password):
        log.warning('Failed login for user %s', username)
        return None

    token = secrets.token_urlsafe()
    csrf_token = secrets.token_urlsafe()
    remote_addr = request.remote_addr
    user_agent = request.headers['User-Agent'] if 'User-Agent' in request.headers else None

    conn.execute("""
                 INSERT INTO session (user, token, csrf_token, creation_date, user_agent, remote_address, last_use)
                 VALUES (?, ?, ?, unixepoch(), ?, ?, unixepoch())
                 """,
                 (user_id, token, csrf_token, user_agent, remote_addr))

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
                          SELECT session.rowid, session.token, session.csrf_token, session.creation_date, session.user_agent,
                                 session.remote_address, session.last_use, user.id, user.username, user.nickname,
                                 user.admin, user.primary_playlist, user.language, user.privacy
                          FROM user
                              INNER JOIN session ON user.id = session.user
                          WHERE session.token=?
                          """, (token,)).fetchone()
    if result is None:
        log.warning('Invalid auth token: %s', token)
        return None

    (session_rowid, session_token, session_csrf_token, session_creation_date, session_user_agent, session_remote_address,
     session_last_use, user_id, username, nickname, admin, primary_playlist, lang_code, privacy_str) = result

    session = Session(session_rowid, session_token, session_csrf_token, session_creation_date, session_user_agent,
                      session_remote_address, session_last_use)

    try:
        remote_addr = request.remote_addr
        user_agent = request.headers['User-Agent'] if 'User-Agent' in request.headers else None
        conn.execute("""
                     UPDATE session
                     SET user_agent=?, remote_address=?, last_use=unixepoch()
                     WHERE rowid=?
                     """,
                     (user_agent, remote_addr, session_rowid))
    except OperationalError as ex:
        # Ignore error if database is read-only
        if ex.sqlite_errorname != 'SQLITE_READONLY':
            raise ex

    return StandardUser(conn, user_id, username, nickname, admin == 1, primary_playlist, lang_code,
                        PrivacyOption(privacy_str), session)


def verify_auth_cookie(conn: Connection, require_admin=False, redirect_to_login=False, require_csrf=False) -> User:
    """
    Verify auth token sent as cookie, raising AuthError if missing or not valid.
    Args:
        conn: Read-only database connection
        require_admin: Whether logging in as a non-admin account should be treated as an authentication failure
        redirect_to_login: Whether the user should sent a redirect if authentication failed, instead
                           of showing a 403 page. Should be set to True for pages, and to False for API endpoints.
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

    if require_csrf:
        if request.content_type == 'application/json':
            csrf_token = request.json['csrf']
        elif request.content_type == 'application/x-www-form-urlencoded' or (request.content_type and request.content_type.startswith('multipart/form-data')):
            csrf_token = request.form['csrf']
        else:
            raise AuthError(AuthErrorReason.MISSING_CSRF, False)

        if not hmac.compare_digest(csrf_token, user.get_csrf()):
            raise AuthError(AuthErrorReason.INVALID_CSRF, False)

    return user


def prune_old_session_tokens(conn: Connection) -> int:
    """
    Prune old session tokens
    Args:
        conn: Read-write database connection
    Returns: Number of deleted tokens
    """
    one_month_ago = int(time.time()) - 60*60*24*30
    return conn.execute('DELETE FROM session WHERE last_use < ?', (one_month_ago,)).rowcount

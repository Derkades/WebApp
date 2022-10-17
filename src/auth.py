import os
import base64
import logging
import time
from typing import Optional
from dataclasses import dataclass
from enum import Enum, unique

import bcrypt
from flask import request
from flask_babel import gettext as _

import db


log = logging.getLogger('app.auth')


@dataclass
class User:
    user_id: int
    username: str
    admin: bool


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


def _generate_session_token() -> str:
    return base64.b64encode(os.urandom(16)).decode()


def log_in(username: str, password: str) -> Optional[str]:
    """
    Log in using username and password.
    Args:
        username
        password
    Returns: Session token, or None if the username+password combination is not valid
    """

    with db.users() as conn:
        result = conn.execute('SELECT id, password FROM user WHERE username=?', (username,)).fetchone()

        if result is None:
            log.warning("Login attempt with non-existent username: '%s'", username)
            return None

        user_id, hashed_password = result

        if not bcrypt.checkpw(password.encode(), hashed_password.encode()):
            log.warning('Failed login for user %s', username)
            return None

        token = _generate_session_token()
        creation_date = int(time.time())

        conn.execute('INSERT INTO session (user, token, creation_date) VALUES (?, ?, ?)',
                     (user_id, token, creation_date))

        log.info('Successful login for user %s', username)

        return token


def verify_token(token: str) -> Optional[User]:
    """
    Verify session token, and return corresponding user
    Args:
        token: Session token to verify
    Returns: User object if session token is valid, or None if invalid
    """
    with db.users() as conn:
        # TODO does this introduce the possibility of a timing attack?
        result = conn.execute("""
                              SELECT user.id, user.username, user.admin
                              FROM user JOIN session ON user.id = session.user
                              WHERE session.token=?
                              """, (token,)).fetchone()
        if result is None:
            log.warning('Invalid auth token: %s', token)
            return None

        user_id, username, admin = result
        return User(user_id, username, admin)


def verify_auth_cookie(require_admin = False, redirect_to_login = False) -> User:
    """
    Verify auth token sent as cookie, raising AuthError if missing or not valid
    """
    if 'token' not in request.cookies:
        log.warning('No auth token')
        raise AuthError(AuthErrorReason.NO_TOKEN, redirect_to_login)

    token = request.cookies['token']
    user = verify_token(token)
    if user is None:
        raise AuthError(AuthErrorReason.INVALID_TOKEN, redirect_to_login)

    if require_admin and not user.admin:
        raise AuthError(AuthErrorReason.ADMIN_REQUIRED, redirect_to_login)

    return user


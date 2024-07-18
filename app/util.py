import base64
import hashlib
import hmac
import logging
import os

from flask import request

from app import jsonw

log = logging.getLogger('app.util')


def check_filename(name: str) -> None:
    """
    Ensure file name is valid, if not raise ValueError
    """
    if '/' in name or name == '.' or name == '..':
        raise ValueError('illegal name')


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


def verify_password(password: str, hashed_password: str) -> bool:
    if hashed_password.startswith('$2b'):
        # Legacy bcrypt password
        log.warning('Logged in using legacy bcrypt password')
        import bcrypt # only import bcrypt when actually required
        return bcrypt.checkpw(password.encode(), hashed_password.encode())

    hash_json = jsonw.from_json(hashed_password)
    if hash_json['alg'] == 'scrypt':
        hash_bytes = hashlib.scrypt(password.encode(),
                                    salt=base64.b64decode(hash_json['salt']),
                                    n=hash_json['n'],
                                    r=hash_json['r'],
                                    p=hash_json['p'])
        return hmac.compare_digest(hash_bytes, base64.b64decode(hash_json['hash']))

    raise ValueError('Unknown alg: ' + hash_json['alg'])


def is_mobile() -> bool:
    """
    Checks whether User-Agent looks like a mobile device (Android or iOS)
    """
    if 'User-Agent' in request.headers:
        user_agent = request.headers['User-Agent']
        if 'Android' in user_agent or 'iOS' in user_agent:
            return True
    return False

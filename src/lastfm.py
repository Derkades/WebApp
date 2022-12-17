import hashlib
from urllib.parse import quote as urlencode

import requests

import settings
import db
from auth import User


CONNECT_URL = 'https://www.last.fm/api/auth/?api_key=' + settings.lastfm_api_key


def _make_request(method: str, api_method: str, **extra_params):
    params = {
        'api_key': settings.lastfm_api_key,
        'method': api_method,
        'format': 'json',
        **extra_params,
    }
    # last.fm API requires alphabetically sorted parameters for signature
    items = sorted(params.items())
    query_string = '&'.join(f'{urlencode(k)}={urlencode(v)}' for k, v in items)
    sig = b''.join(f'{k}{v}'.encode() for k, v in items if k != 'format') + settings.lastfm_api_secret.encode()
    print('sig', sig)
    sig_digest = hashlib.md5(sig).hexdigest()
    query_string += f'&api_sig={sig_digest}'
    print('query_string', query_string)
    if method == 'post':
        r = requests.post('https://ws.audioscrobbler.com/2.0/',
                          data=query_string,
                          headers={'User-Agent': settings.user_agent,
                                   'Content-Type': 'application/x-www-form-urlencoded'})
    elif method == 'get':
        r = requests.get('https://ws.audioscrobbler.com/2.0/?' + query_string,
                         headers={'User-Agent': settings.user_agent})
    else:
        raise ValueError
    print(r.text)
    r.raise_for_status()
    return r.json()


def obtain_session_key(user: User, auth_token: str) -> str:
    """
    Fetches session key from last.fm API and saves it to the database
    Params:
        auth_token
    Returns: last.fm username
    """
    json = _make_request('get', 'auth.getSession', token=auth_token)
    name = json['session']['name']
    key = json['session']['key']

    with db.users() as conn:
        conn.execute('INSERT OR REPLACE INTO user_lastfm (user, name, key) VALUES (?, ?, ?)',
                     (user.user_id, name, key))

    return name

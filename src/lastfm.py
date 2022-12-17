import hashlib
from urllib.parse import quote as urlencode
import logging
from typing import Optional

import requests

import settings
import db
from auth import User
from metadata import Metadata


CONNECT_URL = 'https://www.last.fm/api/auth/?api_key=' + settings.lastfm_api_key

log = logging.getLogger('app.radio')


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
    sig_digest = hashlib.md5(sig).hexdigest()
    query_string += f'&api_sig={sig_digest}'
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
    log.info('lastfm response: %s', r.text)
    r.raise_for_status()
    return r.json()


def _get_key(user: User) -> Optional[str]:
    with db.users() as conn:
        result = conn.execute('SELECT key FROM user_lastfm WHERE user=?',
                            (user.user_id,)).fetchone()
        return result[0] if result else None


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


def update_now_playing(user: User, metadata: Metadata):
    if not metadata.artists or not metadata.title:
        log.info('Skipped update_now_playing, missing metadata')
        return

    key = _get_key(user)
    if not key:
        log.info('Skipped update_now_playing, account is not linked')
        return

    _make_request('post', 'track.updateNowPlaying',
                  artist=metadata.artists[0],
                  track=metadata.title,
                  sk=key)


def scrobble(user: User, metadata: Metadata, start_timestamp: int):
    if not metadata.artists or not metadata.title:
        log.info('Skipped scrobble, missing metadata')
        return

    key = _get_key(user)
    if not key:
        log.info('Skipped scrobble, account is not linked')
        return

    _make_request('post', 'track.scrobble',
                  artist=metadata.artists[0],
                  track=metadata.title,
                  chosenByUser='0',
                  timestamp=str(start_timestamp),
                  sk=key)

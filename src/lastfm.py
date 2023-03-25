import hashlib
from urllib.parse import quote as urlencode
import logging

import requests

import settings
from auth import User
from metadata import Metadata


CONNECT_URL = 'https://www.last.fm/api/auth/?api_key=' + settings.lastfm_api_key

log = logging.getLogger('app.radio')


def is_configured() -> bool:
    return bool(settings.lastfm_api_key) and bool(settings.lastfm_api_secret)


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
                          timeout=10,
                          headers={'User-Agent': settings.user_agent,
                                   'Content-Type': 'application/x-www-form-urlencoded'})
    elif method == 'get':
        r = requests.get('https://ws.audioscrobbler.com/2.0/?' + query_string,
                         timeout=10,
                         headers={'User-Agent': settings.user_agent})
    else:
        raise ValueError
    log.info('lastfm response: %s', r.text)
    r.raise_for_status()
    return r.json()


def get_user_key(user: User) -> str | None:
    """
    Get a user's last.fm session key from local database
    Returns session key, or None if the user has not set up last.fm
    """
    result = user.conn.execute('SELECT key FROM user_lastfm WHERE user=?',
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
    user.conn.execute('INSERT OR REPLACE INTO user_lastfm (user, name, key) VALUES (?, ?, ?)',
                     (user.user_id, name, key))

    return name


def update_now_playing(user_key: str, metadata: Metadata):
    if not is_configured():
        log.info('Skipped scrobble, last.fm not configured')
        return

    if not metadata.artists or not metadata.title:
        log.info('Skipped update_now_playing, missing metadata')
        return

    _make_request('post', 'track.updateNowPlaying',
                  artist=metadata.artists[0],
                  track=metadata.title,
                  sk=user_key)


def scrobble(user_key: str, metadata: Metadata, start_timestamp: int):
    if not is_configured():
        log.info('Skipped scrobble, last.fm not configured')
        return

    if metadata.title and metadata.album_artist:
        artist = metadata.album_artist
    elif metadata.title and metadata.artists:
        artist = ' & '.join(metadata.artists)
    else:
        log.info('Skipped scrobble, missing metadata')
        return

    _make_request('post', 'track.scrobble',
                  artist=artist,
                  track=metadata.title,
                  chosenByUser='0',
                  timestamp=str(start_timestamp),
                  sk=user_key)

    log.info('Scrobbled to last.fm: %s - %s', artist, metadata.title)

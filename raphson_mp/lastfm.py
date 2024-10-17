import hashlib
import logging
from typing import Any
from urllib.parse import quote as urlencode

import requests

from raphson_mp import metadata, settings
from raphson_mp.auth import StandardUser
from raphson_mp.metadata import Metadata

log = logging.getLogger(__name__)


if settings.offline_mode:
    # Module must not be imported to ensure no data is ever downloaded in offline mode.
    raise RuntimeError('Cannot use last.fm in offline mode')


def get_connect_url() -> str | None:
    if not settings.lastfm_api_key:
        return None

    return 'https://www.last.fm/api/auth/?api_key=' + settings.lastfm_api_key


def is_configured() -> bool:
    """Check whether last.fm API key is set"""
    return bool(settings.lastfm_api_key) and bool(settings.lastfm_api_secret)


def _make_request(method: str, api_method: str, **extra_params) -> dict[Any, Any]:
    params = {
        'api_key': settings.lastfm_api_key,
        'method': api_method,
        'format': 'json',
        **extra_params,
    }
    # last.fm API requires alphabetically sorted parameters for signature
    items = sorted(params.items())
    query_string = '&'.join(f'{urlencode(k)}={urlencode(v)}' for k, v in items)
    secret = settings.lastfm_api_secret.encode()
    sig = b''.join(f'{k}{v}'.encode() for k, v in items if k != 'format') + secret
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


def get_user_key(user: StandardUser) -> str | None:
    """
    Get a user's last.fm session key from local database
    Returns session key, or None if the user has not set up last.fm
    """
    result = user.conn.execute('SELECT key FROM user_lastfm WHERE user=?',
                               (user.user_id,)).fetchone()
    return result[0] if result else None


def obtain_session_key(user: StandardUser, auth_token: str) -> str:
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


def update_now_playing(user_key: str, meta: Metadata):
    """Send now playing status to last.fm"""
    # TODO rate limit
    if not is_configured():
        log.info('Skipped scrobble, last.fm not configured')
        return

    if not meta.artists or not meta.title:
        log.info('Skipped update_now_playing, missing metadata')
        return

    _make_request('post', 'track.updateNowPlaying',
                  artist=meta.artists[0],
                  track=meta.title,
                  sk=user_key)


def scrobble(user_key: str, meta: Metadata, start_timestamp: int):
    """Send played track to last.fm"""
    if not is_configured():
        log.info('Skipped scrobble, last.fm not configured')
        return

    if meta.title and meta.album_artist:
        artist = meta.album_artist
    elif meta.title and meta.artists:
        artist = ' & '.join(meta.artists)
    else:
        log.info('Skipped scrobble, missing metadata')
        return

    params = {
        'artist': artist,
        'track': meta.title,
        'chosenByUser': '0',
        'timestamp': str(start_timestamp),
        'sk': user_key,
    }

    if meta.album and not metadata.ignore_album(meta.album):
        params['album'] = meta.album

    _make_request('post', 'track.scrobble', **params)

    log.info('Scrobbled to last.fm: %s - %s', artist, meta.title)

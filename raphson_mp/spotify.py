import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import quote

import requests

from raphson_mp import settings

log = logging.getLogger(__name__)

@dataclass
class SpotifyTrack:
    title: str
    artists: list[str]

    @property
    def display(self) -> str:
        return ', '.join(self.artists) + ' - ' + self.title


class SpotifyClient:

    _access_token: str | None = None
    _access_token_expiry: int = 0

    @property
    def access_token(self) -> str:
        if self._access_token is not None:
            if self._access_token_expiry > int(time.time()):
                return self._access_token

        response= requests.post('https://accounts.spotify.com/api/token',
                                    data={'grant_type': 'client_credentials',
                                          'client_id': settings.spotify_api_id,
                                          'client_secret': settings.spotify_api_secret},
                                    headers={'User-Agent': settings.user_agent},
                                    timeout=10)
        response.raise_for_status()
        access_token: str = response.json()['access_token']
        self._access_token = access_token
        self._access_token_expiry = int(time.time()) + response.json()['expires_in']
        return access_token

    def get_playlist(self, playlist_id: str) -> Iterator[SpotifyTrack]:
        url = 'https://api.spotify.com/v1/playlists/' + quote(playlist_id) + '/tracks'

        while url:
            log.info('making request to: %s', url)
            response = requests.get(url,
                                    params={'fields': 'next,items(track(name,artists(name)))'},
                                    headers={'Authorization': 'Bearer ' + self.access_token,
                                             'User-Agent': settings.user_agent},
                                    timeout=10)
            response.raise_for_status()

            json = response.json()

            for track in json['items']:
                title = track['track']['name']
                artists = [artist['name'] for artist in track['track']['artists']]
                yield SpotifyTrack(title, artists)

            url = json['next']

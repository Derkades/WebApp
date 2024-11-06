from collections.abc import Iterator
import logging
from pathlib import Path
import time
import requests
from raphson_mp import settings
from urllib.parse import quote
from dataclasses import dataclass


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
                                    timeout=10)
        response.raise_for_status()
        access_token: str = response.json()['access_token']
        self._access_token = access_token
        self._access_token_expiry = int(time.time()) + response.json()['expires_in']
        return access_token

    def get_playlist(self, playlist_id: str) -> Iterator[SpotifyTrack]:
        url = 'https://api.spotify.com/v1/playlists/' + quote(playlist_id)

        while url:
            log.info('making request to: %s', url)
            response = requests.get(url,
                                    params={'fields': 'tracks.next,tracks.items(track(name,artists(name))),next,items(track(name,artists(name)))'},
                                    headers={'Authorization': 'Bearer ' + self.access_token},
                                    timeout=10)
            response.raise_for_status()

            json = response.json()
            if 'tracks' in json:
                tracks_json = json['tracks']
            else:
                tracks_json = json

            for track in tracks_json['items']:
                title = track['track']['name']
                artists = [artist['name'] for artist in track['track']['artists']]
                yield SpotifyTrack(title, artists)

            url = tracks_json['next']

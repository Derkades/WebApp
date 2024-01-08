import subprocess
import tempfile
from abc import ABC, abstractmethod
import logging

import feedparser
import requests

from app import cache, settings


log = logging.getLogger('app.news')


class NewsProvider(ABC):
    @abstractmethod
    def get_audio(self) -> bytes:
        """
        Get news bulletin audio bytes
        """


class Nu(NewsProvider):
    def get_audio(self) -> bytes:
        log.info('Downloading onmy.fm RSS feed')
        feed = feedparser.parse('https://omny.fm/shows/nu-nl-nieuws/playlists/podcast.rss')
        log.info('Downloading first news fragment')
        r = requests.get(feed.entries[0].links[0].href, timeout=10)
        audio_bytes = r.content

        log.info('Transcoding news fragment')

        with tempfile.NamedTemporaryFile() as temp_input, tempfile.NamedTemporaryFile() as temp_output:
            temp_input.write(audio_bytes)

            duration = float(subprocess.run(['ffprobe',
                                             temp_input.name,
                                             '-show_entries', 'format=duration',
                                             '-of', 'csv=p=0'],
                                            shell=False,
                                            check=True,
                                            capture_output=True).stdout)

            command = ['ffmpeg',
                       '-y',  # overwriting file is required, because the created temp file already exists
                       '-hide_banner',
                       '-nostats',
                       '-loglevel', settings.ffmpeg_loglevel,
                       '-i', temp_input.name,
                       '-map', '0:a',
                       '-t', str(duration - 4.9),
                       '-f', 'webm',
                       '-c:a', 'libopus',
                       '-b:a', '64k',
                       '-vbr', 'on',
                       temp_output.name]

            subprocess.run(command, shell=False, check=True)
            audio_bytes = temp_output.read()

        return audio_bytes


NEWS_PROVIDERS = {
    'nu.nl': Nu()
}


def get_audio(provider: str):
    cached = cache.retrieve('news' + provider, return_expired=False)
    if cached is not None:
        return cached

    audio_bytes = NEWS_PROVIDERS[provider].get_audio()
    cache.store('news' + provider, audio_bytes, duration=15*60)
    return audio_bytes

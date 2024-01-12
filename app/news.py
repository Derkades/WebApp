import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod

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
    def get_news_url(self) -> str:
        cached = cache.retrieve('nu.nl url', return_expired=False)
        if cached is not None:
            log.info('Returning RSS latest audio URL from cache')
            return cached.decode()

        log.info('Downloading onmy.fm RSS feed')
        feed = feedparser.parse('https://omny.fm/shows/nu-nl-nieuws/playlists/podcast.rss')
        url: str = feed.entries[0].links[0].href
        cache.store('nu.nl url', url.encode(), duration=60*15)
        return url

    def get_audio(self) -> bytes:
        url = self.get_news_url()

        cached = cache.retrieve(url)
        if cached is not None:
            log.info('Returning audio from cache')
            return cached

        log.info('Downloading audio')
        response = requests.get(url, timeout=10)
        audio_bytes = response.content

        with tempfile.NamedTemporaryFile() as temp_input, tempfile.NamedTemporaryFile() as temp_output:
            temp_input.write(audio_bytes)

            log.info('Transcoding news fragment')

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

        cache.store(url, audio_bytes, duration=cache.DAY)

        return audio_bytes


NEWS_PROVIDERS = {
    'nu.nl': Nu()
}


def get_audio(provider: str):
    return NEWS_PROVIDERS[provider].get_audio()

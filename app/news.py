import logging
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod

import feedparser
import requests

from app import cache, settings

log = logging.getLogger('app.news')


class NewsProvider(ABC):
    def __init__(self, start_trim: float, end_trim: float):
        self.start_trim = start_trim
        self.end_trim = end_trim

    @abstractmethod
    def get_audio_url(self) -> str:
        pass

    def _get_duration(self, audio_file_path) -> float:
        result = subprocess.run(['ffprobe', audio_file_path,
                                 '-show_entries', 'format=duration',
                                 '-of', 'csv=p=0'],
                                shell=False,
                                check=True,
                                capture_output=True)
        return float(result.stdout)

    def get_audio(self) -> bytes:
        audio_url = self.get_audio_url()

        cached_audio = cache.retrieve('news_audio' + audio_url)
        if cached_audio:
            log.info('Returning cached audio')
            return cached_audio

        log.info('Downloading audio: %s', audio_url)
        response = requests.get(audio_url,
                                headers={'User-Agent': settings.webscraping_user_agent},
                                timeout=10)
        response.raise_for_status()
        audio_bytes = response.content

        with tempfile.NamedTemporaryFile() as temp_input, tempfile.NamedTemporaryFile() as temp_output:
            temp_input.write(audio_bytes)

            log.info('Transcoding news fragment')

            duration = self._get_duration(temp_input.name)

            command = ['ffmpeg',
                       '-y',  # overwriting file is required, because the created temp file already exists
                       '-hide_banner',
                       '-nostats',
                       '-loglevel', settings.ffmpeg_loglevel,
                       '-ss', str(self.start_trim),
                       '-i', temp_input.name,
                       '-map', '0:a',
                       '-t', str(duration - self.start_trim - self.end_trim),
                       '-f', 'webm',
                       '-c:a', 'libopus',
                       '-b:a', '64k',
                       '-vbr', 'on',
                       '-filter:a', 'loudnorm',
                       temp_output.name]

            subprocess.run(command, shell=False, check=True)
            audio_bytes = temp_output.read()

        cache.store('news_audio' + audio_url, audio_bytes, cache.DAY)

        return audio_bytes

class RSSNewsProvider(NewsProvider):
    def __init__(self, start_trim: float, end_trim: float, feed_url: str):
        super().__init__(start_trim, end_trim)
        self.feed_url = feed_url

    def _get_feed(self):
        log.info('Downloading RSS feed: %s', self.feed_url)
        return feedparser.parse(self.feed_url)

    def _get_latest_url_from_feed(self):
        feed = self._get_feed()
        return feed.entries[0].enclosures[0].href

    def get_audio_url(self) -> str:
        cached_url = cache.retrieve('latest audio' + self.feed_url, return_expired=False)
        if cached_url:
            log.info('Returning latest audio URL from cache')
            return cached_url.decode()

        url = self._get_latest_url_from_feed()
        cache.store('latest audio' + self.feed_url, url.encode(), 15*60)
        return url

class Nu(RSSNewsProvider):
    def __init__(self):
        super().__init__(0, 4.9, 'https://omny.fm/shows/nu-nl-nieuws/playlists/podcast.rss')


class NPR(RSSNewsProvider):
    def __init__(self):
        super().__init__(0, 0, 'https://feeds.npr.org/500005/podcast.xml')


class BBCNews(RSSNewsProvider):
    def __init__(self):
        super().__init__(0, 0, 'https://podcast.voice.api.bbci.co.uk/rss/audio/p002vsmz?api_key=JqAy8fGqi8lpxLsr3WaGxyG31AZ5URMr')

NEWS_PROVIDERS: dict[str, NewsProvider] = {
    'nu.nl': Nu(),
    'npr': NPR(),
    'bbc': BBCNews(),
}


def get_audio(provider: str):
    return NEWS_PROVIDERS[provider].get_audio()


def main():
    audio_bytes = get_audio(sys.argv[1])
    (settings.app_dir / 'news.webm').write_bytes(audio_bytes)


if __name__ == '__main__':
    from app import logconfig
    logconfig.apply()
    main()

import difflib
import html
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Final, override

import requests

from raphson_mp import cache, settings

log = logging.getLogger(__name__)


@dataclass
class LyricsLine:
    start_time: float
    text: str


class Lyrics(ABC):
    source: str


@dataclass
class TimeSyncedLyrics(Lyrics):
    source: str
    text: list[LyricsLine]

    def to_lrc(self) -> str:
        # TODO proper time format
        return '\n'.join([f'[{line.start_time}] {line.text}' for line in self.text])

    def to_plain(self) -> 'PlainLyrics':
        text = '\n'.join([line.text for line in self.text])
        return PlainLyrics(self.source, text)

    @classmethod
    def from_lrc(cls, source: str, lrc: str):
        lines: list[LyricsLine] = []
        for line in lrc.splitlines():
            minutes, seconds, centiseconds, text = re.findall(r'\[(\d{2}):(\d{2})\.(\d{2})\] (.*)', line)[0]
            lines.append(LyricsLine(int(minutes) * 60 + int(seconds) + int(centiseconds) / 100, text))
        return cls(source, lines)


@dataclass
class PlainLyrics(Lyrics):
    source: str
    text: str


def _strmatch(a: str, b: str):
    is_match = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.8
    if not is_match:
        log.info("strings don't match: '%s' '%s'", a, b)
    return is_match


class LyricsFetcher(ABC):
    name: str
    supports_synced: bool

    @abstractmethod
    def find(self, title: str, artist: str, album: str | None, duration: int | None) -> Lyrics | None:
        pass


class LrcLibFetcher(LyricsFetcher):
    name = 'lrclib.net'
    supports_synced = True

    def find(self, title: str, artist: str, album: str | None, duration: int | None) -> Lyrics | None:
        params = {'track_name': title, 'artist_name': artist}
        if album is not None:
            params['album_name'] = album
        if duration is not None:
            params['duration'] = duration
        response = requests.get('https://lrclib.net/api/get',
                                params=params,
                                timeout=5,
                                headers={'User-Agent': settings.user_agent})
        if response.status_code != 404:
            response.raise_for_status()
            json = response.json()
        else:
            log.info('lrclib: no results for direct get, trying search')
            response = requests.get('https://lrclib.net/api/search',
                                    params={'artist_name': artist,
                                            'track_name': title},
                                    timeout=5,
                                    headers={'User-Agent': settings.user_agent})
            response.raise_for_status()
            json = response.json()
            if len(json) == 0:
                return None
            json = json[0]

            # Sanity check on title and artist
            if not _strmatch(artist, json['artistName']):
                return None
            if not _strmatch(title, json['trackName']):
                return None

        if json['syncedLyrics']:
            return TimeSyncedLyrics.from_lrc('LRCLIB ' + str(json['id']), json['syncedLyrics'])

        if json['plainLyrics']:
            return PlainLyrics('LRCLIB ' + str(json['id']), json['plainLyrics'])

        return None


class MusixMatchFetcher(LyricsFetcher):
    """
    Adapted from: https://gitlab.com/ronie/script.cu.lrclyrics/-/blob/master/lib/culrcscrapers/musixmatchlrc/lyricsScraper.py
    Licensed under GPL v2
    """
    name = 'MusixMatch'
    supports_synced = True

    _SEARCH_URL = 'https://apic-desktop.musixmatch.com/ws/1.1/%s'
    _session = requests.Session
    _cached_token: str | None = None
    _cached_token_expiration_time: int = 0

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"authority": "apic-desktop.musixmatch.com",
                                     "cookie": "AWSELBCORS=0; AWSELB=0",
                                     "User-Agent": settings.webscraping_user_agent})

    def get_token(self) -> str:
        if self._cached_token and int(time.time()) < self._cached_token_expiration_time:
            return self._cached_token

        url = self._SEARCH_URL % 'token.get'
        query = {'user_language': 'en', 'app_id': 'web-desktop-app-v1.0', 't': int(time.time())}
        response = self._session.get(url, params=query, timeout=10)
        result = response.json()
        if 'message' in result and 'body' in result["message"] and 'user_token' in result["message"]["body"]:
            self._cached_token = result["message"]["body"]["user_token"]
            self._cached_token_expiration_time = int(time.time()) + 600
            return self._cached_token

        raise ValueError('could not obtain token', result)

    def get_lyrics_from_list(self, track_id):
        url = self._SEARCH_URL % 'track.subtitle.get'
        query = [('track_id', track_id), ('subtitle_format', 'lrc'), ('app_id', 'web-desktop-app-v1.0'), ('usertoken', self.get_token()), ('t', int(time.time()))]
        response = self._session.get(url, params=query, timeout=10)
        result = response.json()

        if 'message' in result and 'body' in result["message"] and 'subtitle' in result["message"]["body"] and 'subtitle_body' in result["message"]["body"]["subtitle"]:
            lyrics = result["message"]["body"]["subtitle"]["subtitle_body"]
            return lyrics

        log.warning('unexpected response: %s', result)
        return None

    @override
    def find(self, title: str, artist: str, album: str | None, duration: int | None):
        url = self._SEARCH_URL % 'track.search'
        query = [('q', title + ' ' + artist), ('page_size', '5'), ('page', '1'), ('app_id', 'web-desktop-app-v1.0'), ('usertoken', self.get_token()), ('t', int(time.time()))]
        response = self._session.get(url, params=query, timeout=10)
        try:
            result = response.json()
        except json.JSONDecodeError:
            log.warning('failed to decode json: %s', response.text)
            return None

        if 'message' in result and 'body' in result["message"] and 'track_list' in result["message"]["body"] and result["message"]["body"]["track_list"]:
            for item in result["message"]["body"]["track_list"]:
                found_artist = item['track']['artist_name']
                found_title = item['track']['track_name']
                found_track_id = item['track']['track_id']
                log.info('musixmatch: search result: %s: %s - %s', found_track_id, found_artist, found_title)
                if _strmatch(title, found_title) and _strmatch(artist, found_artist):
                    lyrics = self.get_lyrics_from_list(found_track_id)
                    if lyrics is not None:
                        return TimeSyncedLyrics.from_lrc('MusixMatch', lyrics)

        return None


class AZLyricsFetcher(LyricsFetcher):
    """
    Adapted from: https://gitlab.com/ronie/script.cu.lrclyrics/-/blob/master/lib/culrcscrapers/azlyrics/lyricsScraper.py
    Licensed under GPL v2
    """
    name = 'AZLyrics'
    supports_synced = False

    @override
    def find(self, title: str, artist: str, album: str | None, duration: int | None) -> PlainLyrics | None:
        artist = re.sub("[^a-zA-Z0-9]+", "", artist).lower().lstrip('the ')
        title = re.sub("[^a-zA-Z0-9]+", "", title).lower()
        url = f'https://www.azlyrics.com/lyrics/{artist}/{title}.html'
        response = requests.get(url,
                                timeout=10,
                                headers={'User-Agent': settings.webscraping_user_agent})
        if response.status_code == 404:
            return None
        response.raise_for_status()
        lyricscode = response.text.split('t. -->')[1].split('</div')[0]
        lyricstext = html.unescape(lyricscode).replace('<br />', '\n')
        lyrics = re.sub('<[^<]+?>', '', lyricstext)
        return PlainLyrics(url, lyrics)


class GeniusFetcher(LyricsFetcher):
    name = 'Genius'
    supports_synced = False

    @override
    def find(self, title: str, artist: str, album: str | None, duration: int | None) -> PlainLyrics | None:
        url = self._search(title, artist)
        if url is None:
            return None

        lyrics = self._extract_lyrics(url)
        if lyrics is None:
            return None

        return PlainLyrics(url, lyrics)


    def _search(self, title: str, artist: str) -> str | None:
        """
        Returns: URL of genius lyrics page, or None if no page was found.
        """
        r = requests.get("https://genius.com/api/search/multi",
                        timeout=10,
                        params={"per_page": "1", "q": title + ' ' + artist},
                        headers={'User-Agent': settings.webscraping_user_agent})

        search_json = r.json()
        for section in search_json["response"]["sections"]:
            if section['type'] == 'top_hit':
                for hit in section['hits']:
                    if hit['index'] == 'song':
                        if _strmatch(title, hit['result']['title']):
                            return hit['result']['url']
                break

        return None

    def _html_to_lyrics(self, html: str) -> str:
        # Extract text from HTML tags
        # Source HTML contains <p>, <b>, <i>, <a> etc. with lyrics inside.
        class Parser(HTMLParser):
            text: str = ''

            def __init__(self):
                HTMLParser.__init__(self)

            @override
            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
                if tag == 'br':
                    self.text += "\n"

            @override
            def handle_data(self, data: str):
                self.text += data.strip()

        parser = Parser()
        parser.feed(html)
        return parser.text

    def _extract_lyrics(self, genius_url: str) -> str | None:
        """
        Extract lyrics from the supplied Genius lyrics page
        Parameters:
            genius_url: Lyrics page URL
        Returns: A list where each element is one lyrics line.
        """
        # Firstly, a request is made to download the standard Genius lyrics page. Inside this HTML is
        # a bit of inline javascript.
        r = requests.get(genius_url,
                        timeout=10,
                        headers={'User-Agent': settings.webscraping_user_agent})
        text = r.text

        # Find the important bit of javascript using these known parts of the code
        start = text.index('window.__PRELOADED_STATE__ = JSON.parse(') + 41
        end = start + text[start:].index("}');") + 1

        # Inside the javascript bit that has now been extracted, is a string. This string contains
        # JSON data. Because it is in a string, some characters are escaped. These need to be
        # un-escaped first.
        info_json_string = text[start:end] \
            .replace('\\"', "\"") \
            .replace("\\'", "'") \
            .replace('\\\\', '\\') \
            .replace('\\$', '$') \
            .replace('\\`', '`')

        # Now, the JSON object is ready to be parsed.
        try:
            info_json = json.loads(info_json_string)
        except json.decoder.JSONDecodeError as ex:
            log.info('Error retrieving lyrics: json decode error at %s', ex.pos)
            log.info('Neighbouring text: "%s"', info_json_string[ex.pos-20:ex.pos+20])
            raise ex

        # For some reason, the JSON object happens to contain lyrics HTML. This HTML is parsed.
        lyrics_html = info_json['songPage']['lyricsData']['body']['html']
        lyrics_text = self._html_to_lyrics(lyrics_html)
        if lyrics_text.lower() in {'instrumental', '[instrumental]', '[instrument]', '(instrumental)', '♫ instrumental ♫'}:
            return None
        return lyrics_text


if settings.offline_mode:
    # set fetchers to an empty list, as an additional safety measure to ensure no data is used in offline mode
    FETCHERS: Final[list[LyricsFetcher]] = []
else:
    FETCHERS: Final[list[LyricsFetcher]] = [
        LrcLibFetcher(), # No rate limit
        MusixMatchFetcher(), # Strict rate limiting
        GeniusFetcher(), # Relaxed rate limiting, no time-synced lyrics
        AZLyricsFetcher(), # Unknown rate limiting, no time-synced lyrics
    ]


def _find(title: str, artist: str, album: str | None, duration: int | None) -> Lyrics | None:
    assert title is not None and artist is not None, "title and artist are required"

    log.info('fetching lyrics for: %s - %s', artist, title)

    plain_match: Lyrics | None = None

    for fetcher in FETCHERS:
        if plain_match is not None and not fetcher.supports_synced:
            # if we already have plain lyrics, we do not need to try any fetchers that only support plain lyrics
            continue

        try:
            lyrics = fetcher.find(title, artist, album, duration)
        except:
            log.exception('%s: encountered an error', fetcher.name)
            continue

        if lyrics is None:
            log.info('%s: no lyrics found, continuing search', fetcher.name)
            continue

        if isinstance(lyrics, TimeSyncedLyrics):
            log.info('%s: found time-synced lyrics', fetcher.name)
            return lyrics

        if plain_match:
            log.info('%s, no time-synced lyrics found, continuing search', fetcher.name)
            continue

        if isinstance(lyrics, PlainLyrics):
            log.info('%s: found plain lyrics, continuing search', fetcher.name)
            plain_match = lyrics
            continue

        raise ValueError(lyrics)

    if plain_match is not None:
        log.info('Returning plain lyrics')
        return plain_match

    log.info('No lyrics found')
    return None


def to_dict(lyrics: Lyrics | None) -> dict[str, Any]:
    if lyrics is None:
        return {'type': 'none'}
    elif isinstance(lyrics, TimeSyncedLyrics):
        text = [{'start_time': line.start_time, 'text': line.text} for line in lyrics.text]
        return {'type': 'synced', 'source': lyrics.source, 'text': text}
    elif isinstance(lyrics, PlainLyrics):
        return {'type': 'plain', 'source': lyrics.source, 'text': lyrics.text}
    else:
        raise ValueError(lyrics)


def from_dict(dict) -> Lyrics | None:
    if dict['type'] == 'none':
        return None

    if dict['type'] == 'synced':
        lines = [LyricsLine(line['start_time'], line['text']) for line in dict['text']]
        return TimeSyncedLyrics(dict['source'], lines)

    if dict['type'] == 'plain':
        return PlainLyrics(dict['source'], dict['text'])

    raise ValueError(dict['type'])


def find(title: str, artist: str, album: str | None, duration: int | None) -> Lyrics | None:
    assert title is not None and artist is not None, "title and artist are required"

    cache_key = f'lyrics{artist}{title}{album}{duration}'

    cached_dict = cache.retrieve_json(cache_key)
    if cached_dict is not None:
        log.info('returning lyrics from cache')
        return from_dict(cached_dict)
    #     log.info('returning lyrics from cache')
    #     return from_dict(cached_dict)

    lyrics = _find(title, artist, album, duration)

    cached_dict = to_dict(lyrics)
    if lyrics is None:
        duration = cache.MONTH
    else:
        duration = cache.YEAR
    cache.store_json(cache_key, cached_dict, duration)

    return lyrics

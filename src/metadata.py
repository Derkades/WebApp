from pathlib import Path
import subprocess
import re
from typing import Optional, List
import logging
import json

import keyval


log = logging.getLogger('app.cache')


FILENAME_STRIP_KEYWORDS = [
    '(Hardstyle)',
    '(Official Music Video)',
    '[Official Music Video]',
    '(Official Video)',
    '(Official Audio)',
    '[Official Audio]',
    '[Official Video]',
    '(Official Video 4K)',
    '(Official Video HD)',
    '[FREE DOWNLOAD]',
    '(OFFICIAL MUSIC VIDEO)',
    '(live)',
    '[Radio Edit]',
    '(Clip officiel)',
    '(Official videoclip)',
    '_ HQ Videoclip',
    '[Monstercat Release]',
    '[Monstercat Lyric Video]',
    '[Nerd Nation Release]',
    '[Audio]',
    '(Remastered)',
    '_ Napalm Records',
    '| Napalm Records'
    '(Lyrics)',
    '[Official Lyric Video]',
    '(Official Videoclip)',
    '(Visual)',
    '(long version)',
    ' HD',
    '(Single Edit)',
    '(official video)',
]


COLLECTION_KEYWORDS = [
    'top 2000',
    'top 500',
    'top 100',
    'top 40',
    'jaarlijsten',
    'jaargang',
    'super hits',
    'the best of',
    'het beste uit',
    'hitzone',
]


def strip_keywords(inp: str) -> str:
    """
    Remove undesirable keywords from title, as a result of being downloaded from the internet.
    """
    for strip_keyword in FILENAME_STRIP_KEYWORDS:
        inp = inp.replace(strip_keyword, '')
    return inp


def is_alpha(c):
    """
    Check whether given character is alphanumeric, a dash or a space
    """
    return c == ' ' or \
           c == '-' or \
           'a' <= c <= 'z' or \
           'A' <= c <= 'Z' or \
           '0' <= c <= '9'


class Metadata:

    path: str
    duration: int
    artists: Optional[List[str]] = None
    album: Optional[str] = None
    title: Optional[str] = None
    date: Optional[str] = None
    year: Optional[str] = None
    album_artist: Optional[str] = None
    genres: List[str]

    def __init__(self, path: Path):
        self.path = path

        cache_key = 'ffprobe' + path.absolute().as_posix()
        output_bytes = keyval.conn.get(cache_key)
        if output_bytes is None:
            command = [
                'ffprobe',
                '-print_format', 'json',
                '-show_entries', 'format',
                path.absolute().as_posix(),
            ]
            try:
                result = subprocess.run(command,
                                        shell=False,
                                        check=True,
                                        capture_output=True)
            except subprocess.CalledProcessError as ex:
                log.warning('metadata read error')
                log.warning('stderr: %s', ex.stderr)
                return

            output_bytes = result.stdout
            keyval.conn.set(cache_key, output_bytes)

        data = json.loads(output_bytes.decode())['format']

        self.duration = int(float(data['duration']))
        self.genres = []
        if 'tags' in data:
            for name, value in data['tags'].items():
                # sometimes ffprobe returns tags in uppercase
                name = name.lower()

                if name == 'album':
                    self.album = value

                if name == 'artist':
                    # Split by / and \;
                    # TODO are these still used as separators, now that we've switched to ffprobe?
                    self.artists = re.split(r'\/|\\;', value)

                if name == 'title':
                    self.title = strip_keywords(value).strip()

                if name == 'date':
                    self.date = value
                    self.year = value[:4]

                if name == 'album_artist':
                    self.album_artist = value

                if name == 'genre':
                    # TODO Allow multiple genres, split by some character
                    self.genres.append(value)

    def _meta_title(self) -> Optional[str]:
        """
        Generate title from 'artist', 'title' and 'date' metadata
        Returns: Generated title, or None if the track lacks the required metadata
        """
        if self.artists and self.title:
            title = ' & '.join(self.artists) + ' - ' + self.title
            if self.year:
                title += ' [' + self.year + ']'
            return title
        else:
            return None

    def _filename_title(self) -> str:
        """
        Generate title from file name
        Returns: Title string
        """
        title = self.path.name
        # Remove file extension
        try:
            title = title[:title.rindex('.')]
        except ValueError:
            pass
        # Remove YouTube id suffix
        title = re.sub(r' \[[a-zA-Z0-9\-_]+\]', '', title)
        title = strip_keywords(title)
        title.strip()
        return title

    def _filename_title_search(self) -> str:
        """
        Generate search title from file name. Same as _filename_title(), but
        special characters are removed
        """
        title = self._filename_title()
        # Remove special characters
        title = ''.join([c for c in title if is_alpha(c)])
        title = title.strip()
        return title

    def display_title(self) -> str:
        """
        Generate display title. It is generated using metadata if
        present, otherwise using the file name.
        """
        title = self._meta_title()
        if title:
            return title
        else:
            return self._filename_title() + ' ~'

    def _is_collection_album(self) -> bool:
        """
        Check whether album is a collection based on known keywords
        """
        if self.album is None:
            raise ValueError('album name not known')
        for keyword in COLLECTION_KEYWORDS:
            if keyword in self.album.lower():
                return True
        return False

    def album_release_query(self):
        """
        Get album search query for a music search engine like MusicBrainz
        """
        if self.album_artist:
            artist = self.album_artist
        elif self.artists is not None and len(self.artists) > 0:
            artist = ' '.join(self.artists)
        else:
            artist = None

        if self.album and not self._is_collection_album():
            album = self.album
        elif self.title:
            album = self.title
        else:
            album = None

        if artist and album:
            return artist + ' - ' + album
        else:
            return self._filename_title_search()

    def album_search_queries(self):
        """
        Generate possible search queries to find album art using a general search engine
        """
        if self.album_artist:
            artist = self.album_artist
        elif self.artists is not None and len(self.artists) > 0:
            artist = ' '.join(self.artists)
        else:
            artist = None

        if artist and self.album and not self._is_collection_album():

            yield artist + ' - ' + self.album + ' cover'
            yield artist + ' - ' + self.album

        if artist and self.title:
            yield artist + ' - ' + self.title + ' cover'
            yield artist + ' - ' + self.title

        if self.title:
            yield self.title + ' cover'
            yield self.title

        yield self._filename_title_search()

    def lyrics_search_queries(self):
        """
        Generate possible search queries to find lyrics
        """
        if self.artists and self.title:
            yield ' '.join(self.artists) + ' - ' + self.title

        yield self._filename_title_search()

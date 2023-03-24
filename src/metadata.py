from pathlib import Path
import subprocess
import re
from typing import Optional, Iterator
import logging
import json
from dataclasses import dataclass
from sqlite3 import Connection

import music


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
    '(Audio Officiel)',
    '(Official videoclip)',
    'HQ Videoclip',
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
    'High Quality',
    '[OUT NOW]',
    '(Dance Video)',
    'Offisiell video',
    '[FREE DL]',
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
    'greatest hits',
    'hits collection',
    'top40',
    'hitdossier',
]


def contains_collection_keyword(text: str) -> bool:
    text = text.lower()
    for keyword in COLLECTION_KEYWORDS:
        if keyword in text:
            return True
    return False


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


def join_meta_list(entries: list[str]) -> str:
    return '; '.join(entries)


def split_meta_list(meta_list: str) -> list[str]:
    """
    Split list (stored as string in metadata) by semicolon
    """
    entries = []
    for entry in meta_list.split(';'):
        if entry.strip() != '':
            entries.append(entry.strip())
    return entries

# TODO Move to Track class

@dataclass
class Metadata:

    relpath: str
    duration: int
    artists: Optional[list[str]]
    album: Optional[str]
    title: Optional[str]
    year: Optional[int]
    album_artist: Optional[str]
    track_number: Optional[int]
    tags: list[str]

    def _meta_title(self) -> Optional[str]:
        """
        Generate title from 'artist', 'title' and 'date' metadata
        Returns: Generated title, or None if the track lacks the required metadata
        """
        if self.artists and self.title:
            title = ' & '.join(self.artists) + ' - ' + self.title
            if self.year:
                title += ' [' + str(self.year) + ']'
            return title
        else:
            return None

    def filename_title(self) -> str:
        """
        Generate title from file name
        Returns: Title string
        """
        title = self.relpath.split('/')[-1]
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
        title = self.filename_title()
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
            return self.filename_title() + ' ~'

    def album_release_query(self) -> str:
        """
        Get album search query for a music search engine like MusicBrainz
        """
        if self.album_artist:
            artist = self.album_artist
        elif self.artists is not None and len(self.artists) > 0:
            artist = ' '.join(self.artists)
        else:
            artist = None

        if self.album and not contains_collection_keyword(self.album):
            album = self.album
        elif self.title:
            album = self.title
        else:
            album = None

        if artist and album:
            return artist + ' - ' + album
        else:
            return self._filename_title_search()

    def album_search_queries(self) -> Iterator[str]:
        """
        Generate possible search queries to find album art using a general search engine
        """
        if self.album_artist and not contains_collection_keyword(self.album_artist):
            artist = self.album_artist
        elif self.artists is not None and len(self.artists) > 0:
            artist = ' '.join(self.artists)
        else:
            artist = None

        if artist and self.album and not contains_collection_keyword(self.album):
            yield artist + ' - ' + self.album + ' cover'
            yield artist + ' - ' + self.album

        if artist and self.title:
            yield artist + ' - ' + self.title + ' cover'
            yield artist + ' - ' + self.title

        if self.title:
            yield self.title + ' cover'
            yield self.title

        yield self._filename_title_search()

    def lyrics_search_queries(self) -> Iterator[str]:
        """
        Generate possible search queries to find lyrics
        """
        if self.artists and self.title:
            yield ' '.join(self.artists) + ' - ' + self.title

        yield self._filename_title_search()


def probe(path: Path) -> Metadata:
    """
    Create Metadata object by running ffprobe on a file
    Args:
        path: Path to file
    Returns: Metadata object
    """
    command = [
        'ffprobe',
        '-show_streams',
        '-show_format',
        '-print_format', 'json',
        path.absolute().as_posix(),
    ]

    result = subprocess.run(command,
                            shell=False,
                            check=True,
                            capture_output=True)

    output_bytes = result.stdout

    data = json.loads(output_bytes.decode())

    duration = int(float(data['format']['duration']))
    artists = None
    album = None
    title = None
    year = None
    album_artist = None
    track_number = None
    tags = []

    meta_tags = []

    for stream in data['streams']:
        if stream['codec_type'] == 'audio':
            if 'tags' in stream:
                meta_tags.extend(stream['tags'].items())

    if 'tags' in data['format']:
        meta_tags.extend(data['format']['tags'].items())

    for name, value in meta_tags:
        # sometimes ffprobe returns tags in uppercase
        name = name.lower()

        if name == 'album':
            album = value

        if name == 'artist':
            artists = split_meta_list(value)

        if name == 'title':
            title = strip_keywords(value).strip()

        if name == 'date':
            try:
                year = int(value[:4])
            except ValueError:
                log.warning("Invalid year '%s' in file '%s'", value, path.absolute().as_posix())

        if name == 'album_artist':
            album_artist = value

        if name == 'track':
            try:
                track_number = int(value.split('/')[0])
            except ValueError:
                log.warning("Invalid track number '%s' in file '%s'", value, path.absolute().as_posix())

        if name == 'genre':
            tags = split_meta_list(value)

    return Metadata(music.to_relpath(path), duration, artists, album, title, year, album_artist, track_number, tags)


def cached(conn: Connection, relpath: str) -> Metadata:
    """
    Create Metadata object from database contents
    Returns: Metadata, or None if the track is not known
    """
    query = 'SELECT duration, title, album, album_artist, track_number, year FROM track WHERE path=?'
    row = conn.execute(query, (relpath,)).fetchone()
    if row is None:
        raise ValueError('Missing track from database: ' + relpath)
    duration, title, album, album_artist, track_number, year = row

    rows = conn.execute('SELECT artist FROM track_artist WHERE track=?', (relpath,)).fetchall()
    if len(rows) == 0:
        artists = None
    else:
        artists = [row[0] for row in rows]

    rows = conn.execute('SELECT tag FROM track_tag WHERE track=?', (relpath,)).fetchall()
    tags = [row[0] for row in rows]

    return Metadata(relpath, duration, artists, album, title, year, album_artist, track_number, tags)

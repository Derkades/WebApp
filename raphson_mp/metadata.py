import json
import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from sqlite3 import Connection
from typing import Optional

from raphson_mp import music

log = logging.getLogger(__name__)


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
    'Official Music Video',
]


ALBUM_IGNORE_KEYWORDS = [
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
    '100 beste',
    'top hits',
    'the very best',
    'top trax',
    'ultimate rock collection',
    'absolute music',
]

ALBUM_ARTIST_IGNORE = {
    'various artists',
}


METADATA_ADVERTISEMENT_KEYWORDS = [
    'electronicfresh.com',
    'djsoundtop.com'
]


def ignore_album(album: str) -> bool:
    """Check whether album name should be ignored"""
    album = album.lower()
    for keyword in ALBUM_IGNORE_KEYWORDS:
        if keyword in album:
            return True
    return False


def ignore_album_artist(artist: str) -> bool:
    """Check whether album artist should be ignored"""
    return artist.lower() in ALBUM_ARTIST_IGNORE


def _strip_keywords(inp: str) -> str:
    """
    Remove undesirable keywords from title, as a result of being downloaded from the internet.
    """
    for strip_keyword in FILENAME_STRIP_KEYWORDS:
        inp = inp.replace(strip_keyword, '')
    return inp


def _is_alpha(char: str) -> bool:
    """
    Check whether given character is alphanumeric, a dash or a space
    """
    return char == ' ' or \
           char == '-' or \
           'a' <= char <= 'z' or \
           'A' <= char <= 'Z' or \
           '0' <= char <= '9'


def _join_meta_list(entries: list[str]) -> str:
    """Join list with semicolons"""
    return '; '.join(entries)


def _split_meta_list(meta_list: str) -> list[str]:
    """
    Split list (stored as string in metadata) by semicolon
    """
    entries = []
    for entry in meta_list.split(';'):
        entry = entry.strip()
        if entry != '' and entry not in entries:
            entries.append(entry)
    return entries


def _has_advertisement(metadata_str: str) -> bool:
    """Check whether string contains advertisements and should be ignored"""
    for keyword in METADATA_ADVERTISEMENT_KEYWORDS:
        if keyword in metadata_str.lower():
            return True
    return False


def _sort_artists(artists: Optional[list[str]], album_artist: Optional[str]) -> Optional[list[str]]:
    """
    Move album artist to start of artist list
    """
    if artists and album_artist and album_artist in artists:
        artists.remove(album_artist)
        return [album_artist] + artists

    return artists


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
    lyrics: Optional[str]

    def _meta_title(self) -> Optional[str]:
        """
        Generate title from 'artist', 'title' and 'date' metadata
        Returns: Generated title, or None if the track lacks the required metadata
        """
        if not self.artists or not self.title:
            return None

        title = ', '.join(self.artists) + ' - ' + self.title
        if self.year:
            title += ' [' + str(self.year) + ']'
        return title

    def filename_title(self) -> str:
        """
        Generate title from file name
        Returns: Title string
        """
        title = self.relpath.split('/', maxsplit=1)[-1]
        # Remove file extension
        try:
            title = title[:title.rindex('.')]
        except ValueError:
            pass
        # Remove YouTube id suffix
        title = re.sub(r' \[[a-zA-Z0-9\-_]+\]', '', title)
        title = _strip_keywords(title)
        title.strip()
        return title

    def _filename_title_search(self) -> str:
        """
        Generate search title from file name. Same as _filename_title(), but
        special characters are removed
        """
        title = self.filename_title()
        # Remove special characters
        title = ''.join([c for c in title if _is_alpha(c)])
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
        return self.filename_title()

    def download_name(self) -> str:
        """
        Name for a downloaded file. display_title() with some characters removed.
        """
        return re.sub(r'[^\x00-\x7f]', r'', self.display_title())

    def primary_artist(self) -> Optional[str]:
        if self.artists is not None:
            if len(self.artists) == 1:
                return self.artists[0] # if there is only one artist, it is the primary artist
            elif len(self.artists) > 1:
                # if there are multiple artists, the album artist is probably the primary artist
                if self.album_artist is not None:
                    if self.album_artist in self.artists:
                        return self.album_artist

                # if album artist is not known, we have to guess
                return self.artists[0]

        return None

    def get_ffmpeg_options(self, option='-metadata') -> list[str]:
        metadata_options: list[str] = []
        if self.album:
            metadata_options.extend((option, 'album=' + self.album))
        if self.artists is not None:
            metadata_options.extend((option, 'artist=' + _join_meta_list(self.artists)))
        if self.title is not None:
            metadata_options.extend((option, 'title=' + self.title))
        if self.year is not None:
            metadata_options.extend((option, 'date=' + str(self.year)))
        if self.album_artist is not None:
            metadata_options.extend((option, 'album_artist=' + self.album_artist))
        if self.track_number is not None:
            metadata_options.extend((option, 'track=' + str(self.track_number)))
        if self.lyrics is not None:
            metadata_options.extend((option, 'lyrics=' + str(self.track_number)))
        if self.tags:
            metadata_options.extend((option, 'genre=' + _join_meta_list(self.tags)))
        return metadata_options


def probe(path: Path) -> Metadata | None:
    """
    Create Metadata object by running ffprobe on a file
    Args:
        path: Path to file
    Returns: Metadata object, or None if ffprobe failed to read the file
    """
    command = [
        'ffprobe',
        '-show_streams',
        '-show_format',
        '-print_format', 'json',
        path.resolve().as_posix(),
    ]

    try:
        result = subprocess.run(command,
                                shell=False,
                                check=True,
                                capture_output=True)
    except subprocess.CalledProcessError:
        log.warning('Error scanning track %s, is it corrupt?', path)
        return None

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
    lyrics = None

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

        if _has_advertisement(value):
            log.info('Ignoring advertisement: %s = %s', name, value)
            continue

        if name == 'album':
            album = value

        if name == 'artist':
            artists = _split_meta_list(value)

        if name == 'title':
            title = _strip_keywords(value).strip()

        if name == 'date':
            try:
                year = int(value[:4])
            except ValueError:
                log.warning("Invalid year '%s' in file '%s'", value, path.resolve().as_posix())

        if name == 'album_artist':
            album_artist = value

        if name == 'track':
            try:
                track_number = int(value.split('/')[0])
            except ValueError:
                log.warning("Invalid track number '%s' in file '%s'", value, path.resolve().as_posix())

        if name == 'genre':
            tags = _split_meta_list(value)

        if name in {'lyrics', 'lyrics-en', 'lyrics-eng', 'lyrics-english'}:
            lyrics = value

        # Allow other languages, but only if no other lyrics are available
        if name.startswith('lyrics') and lyrics is None:
            lyrics = value

    return Metadata(music.to_relpath(path),
                    duration,
                    _sort_artists(artists, album_artist),
                    album,
                    title,
                    year,
                    album_artist,
                    track_number,
                    tags,
                    lyrics)


def cached(conn: Connection, relpath: str) -> Metadata:
    """
    Create Metadata object from database contents
    Returns: Metadata, or None if the track is not known
    """
    query = 'SELECT duration, title, album, album_artist, track_number, year, lyrics FROM track WHERE path=?'
    row = conn.execute(query, (relpath,)).fetchone()
    if row is None:
        raise ValueError('Missing track from database: ' + relpath)
    duration, title, album, album_artist, track_number, year, lyrics = row

    rows = conn.execute('SELECT artist FROM track_artist WHERE track=?', (relpath,)).fetchall()
    if len(rows) == 0:
        artists = None
    else:
        artists = [row[0] for row in rows]

    rows = conn.execute('SELECT tag FROM track_tag WHERE track=?', (relpath,)).fetchall()
    tags = [row[0] for row in rows]

    return Metadata(relpath, duration, _sort_artists(artists, album_artist), album, title, year, album_artist, track_number, tags, lyrics)

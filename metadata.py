from pathlib import Path
import subprocess
import re
from typing import Optional, List


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
    '(Lyrics)',
    '[Official Lyric Video]',
    '(Official Videoclip)',
    '(Visual)',
]


def is_alpha(c):
    """
    Check whether given character is alphanumeric, a dash or a space
    """
    return c == ' ' or \
           c == '-' or \
           'a' <= c <= 'z' or \
           'A' <= c <= 'Z'


class Metadata:

    def __init__(self, path: Path, debug = False):
        self.path = path
        self.artists: Optional[List[str]] = None
        self.album: Optional[str] = None
        self.title: Optional[str] = None
        self.date: Optional[str] = None
        self.album_artist: Optional[str] = None

        command = [
            'ffmpeg',
            '-loglevel', 'error',
            '-i', path.absolute().as_posix(),
            '-f', 'ffmetadata',
            '-'
        ]
        try:
            result = subprocess.run(command,
                                shell=False,
                                check=True,
                                capture_output=True,
                                text=True)
        except subprocess.CalledProcessError as ex:
            print('metadata read error')
            print('stderr: ', ex.stderr)
            return

        # Example output:
        # -----------------------------------------------
        # ;FFMETADATA1
        # encoded_by=Switch Trial Version © NCH Software
        # comment=
        # track=3
        # album=Elevator Music For An Elevated Mood
        # artist=Cory Wong/Dave Koz
        # album_artist=Cory Wong
        # title=Restoration (feat. Dave Koz)
        # genre=Jazz
        # date=2020
        # encoder=Lavf58.76.100
        # subprocess.run()
        # -----------------------------------------------

        for line in result.stdout.splitlines():
            try:
                eq = line.index('=')
            except ValueError:
                continue

            key = line[:eq].lower()
            value = line[eq+1:]
            if key == 'album':
                self.album = value
            elif key == 'artist':
                self.artists = value.split('/')
            elif key == 'title':
                self.title = value
            elif key == 'date':
                self.date = value
            elif key == 'album_artist':
                self.album_artist = value

            if debug:
                print(key, value, sep='\t')


    def _meta_title(self) -> Optional[str]:
        """
        Generate title from 'artist', 'title' and 'date' metadata
        Returns: Generated title, or None if the track lacks the required metadata
        """
        if self.artists and self.title:
            title = ' & '.join(self.artists) + ' - ' + self.title
            if self.date:
                title += ' [' + self.date[:4] + ']'
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
        for strip_keyword in FILENAME_STRIP_KEYWORDS:
            title = title.replace(strip_keyword, '')
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
            return self._filename_title() + ' [~]'

    def _is_collection_album(self) -> bool:
        """
        Check whether album is a collection based on known keywords
        """
        if self.album is None:
            raise ValueError('album name not known')
        for match in ['top 500', 'top 40', 'jaarlijsten', 'jaargang', 'super hits']:
            if match in self.album.lower():
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

        if self.album and self._is_collection_album():
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
        if self.album and not self._is_collection_album():
            yield self.album + ' cover'
            yield self.album

        if self.artists and self.title:
            yield ' '.join(self.artists) + ' - ' + self.title + ' cover'
            yield ' '.join(self.artists) + ' - ' + self.title

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


if __name__ == '__main__':
    meta = Metadata(Path('music', 'Guest-Robin', '03. Restoration (feat. Dave Koz).mp3'), debug = True)
    print('---------------------')
    print(meta.display_title())
    print(list(meta.album_search_queries()))
    print(list(meta.lyrics_search_queries()))

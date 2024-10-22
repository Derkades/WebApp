import logging
import re
import traceback
from dataclasses import dataclass
from typing import Any, Iterator, Optional

import requests
from requests.exceptions import HTTPError

from raphson_mp import settings

if settings.offline_mode:
    # Module must not be imported to ensure no data is ever downloaded in offline mode.
    raise RuntimeError('Cannot use musicbrainz in offline mode')


log = logging.getLogger(__name__)


# https://lucene.apache.org/core/4_3_0/queryparser/org/apache/lucene/queryparser/classic/package-summary.html#Escaping_Special_Characters
# https://github.com/alastair/python-musicbrainzngs/blob/1638c6271e0beb9560243c2123d354461ec9f842/musicbrainzngs/musicbrainz.py#L27
LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]\^"~*?:\\\/])')

def lucene_escape(text: str) -> str:
    """Escape string for MB"""
    return re.sub(LUCENE_SPECIAL, r'\\\1', text)


def _mb_get(url: str, params: dict[str, str]) -> dict[str, Any]:
    response = requests.get('https://musicbrainz.org/ws/2/' + url,
                            headers={'Accept': 'application/json',
                                     'User-Agent': settings.user_agent},
                     params=params,
                     timeout=10)
    response.raise_for_status()
    return response.json()


def _caa_get(release_id: str, img_type: str, size: int) -> bytes:
    r = requests.get(f'https://coverartarchive.org/release/{release_id}/{img_type}-{size}',
                     headers={'User-Agent': settings.user_agent},
                     allow_redirects=True,
                     timeout=20)
    r.raise_for_status()
    return r.content


def _search_release_group(artist: str, title: str) -> str | None:
    """
    Search for a release group id using the provided search query
    """
    query = f'artist:"{lucene_escape(artist)}" AND releasegroup:"{lucene_escape(title)}"'
    log.info('Performing MB search for query: %s', query)
    result = _mb_get('release-group',
                        {'query': query,
                        'limit': '1',
                        'primarytype': 'Album'}) # preference for albums, but this is not a strict filter
    groups = result['release-groups']
    if groups:
        group = groups[0]
        log.info('Found release group: %s: %s (%s)', group['id'], group['title'], group['primary-type'])
        return group['id']

    log.info('No release group found')
    return None


def _pick_release(release_group: str) -> str | None:
    """
    Choose a release from a release group, to download cover art
    Returns: release id, or None if no suitable release was found
    """
    result = _mb_get('release',
                     params={'release-group': release_group})
    releases = result['releases']
    with_artwork = [r for r in releases if r['cover-art-archive']['front']]
    if not with_artwork:
        log.info('No releases with artwork available')
        return None

    # Try to find digital release, it usually has the highest quality cover
    for release in with_artwork:
        if 'packaging' in release and release['packaging'] == 'None':
            log.info('Found packaging==None release: %s', release['id'])
            return release['id']

    log.info('Returning first release in release group')
    return with_artwork[0]['id']


def get_cover(artist: str, album: str) -> bytes | None:
    """
    Get album cover for the given artist and album
    Returns: Image bytes, or None of no album cover was found.
    """
    try:
        release_group = _search_release_group(artist, album)
        if release_group is None:
            return None

        release = _pick_release(release_group)

        if release is None:
            return None

        log.info('Downloading artwork from internet archive')
        image_bytes = _caa_get(release, "front", 1200)

        if image_bytes is None:
            log.info('Release has no front cover art image image')
            return None

        return image_bytes
    except Exception as ex:
        log.info('Error retrieving album art from musicbrainz: %s', ex)
        traceback.print_exc()
        return None


@dataclass
class MBMeta:
    id: str
    title: str
    album: str
    artists: list[str]
    album_artist: str
    year: Optional[int]
    release_type: str
    packaging: str


def get_recording_metadata(recording_id: str) -> Iterator[MBMeta]:
    try:
        result = _mb_get('recording/' + recording_id, {'inc': 'artists+releases+release-groups'})
    except HTTPError as ex:
        if ex.response.status_code == 404:
            log.warning('got 404 for recording %s', recording_id)
            return
        raise ex

    title = result['title']
    artists = [artist['name'] for artist in result['artist-credit']]

    for release in result['releases']:
        if 'Compilation' in release['release-group']['secondary-types']:
            log.info('ignoring compilation release: %s', release['id'])
            continue

        release_type = release['release-group']['primary-type']

        album = release['title']

        # Ideally we'd get the correct artist from the release group, but that would require many API requests.
        album_artist = artists[0]

        if 'date' in release and len(release['date']) >= 4:
            year = int(release['date'][:4])
        else:
            year = None

        packaging = release['packaging']
        if packaging is None or packaging == 'None':
            packaging = 'Digital'

        yield MBMeta(release['id'], title, album, artists, album_artist, year, release_type, packaging)

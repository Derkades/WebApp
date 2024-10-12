import logging
import re
import traceback
from pathlib import Path
from typing import Any

import requests

from raphson_mp import settings

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

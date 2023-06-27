import logging
import traceback
import urllib

import musicbrainzngs

import cache
import image

musicbrainzngs.set_useragent('Super fancy music player 2.0', 0.1, 'https://github.com/DanielKoomen/WebApp')

log = logging.getLogger('app.musicbrainz')


def _search_release_group(artist: str, title: str) -> str:
    """
    Search for a release group id using the provided search query
    """
    log.info('Looking for album release group: %s - %s', artist, title)
    result = musicbrainzngs.search_release_groups(title, artist=artist, limit=1, type='album')
    groups = result['release-group-list']
    if groups:
        return groups[0]['id']

    log.info('Looking for single/EP/other release group: %s - %s', artist, title)
    result = musicbrainzngs.search_release_groups(title, artist=artist, limit=1)
    groups = result['release-group-list']
    if groups:
        return groups[0]['id']

    log.info('No release group found')
    return None


def _get_image(release_id: str) -> bytes | None:
    """
    Get album cover URL from MusicBrainz release group id
    """
    try:
        return musicbrainzngs.get_release_group_image_front(release_id, size="1200")
    except musicbrainzngs.musicbrainz.ResponseError as ex:
        if isinstance(ex.cause, urllib.error.HTTPError) and ex.cause.code == 404:
            return None
        raise ex

def get_cover(artist: str, album: str) -> bytes | None:
    """
    Get album cover for the given artist and album
    Returns: Image bytes, or None of no album cover was found.
    """
    cache_key = 'musicbrainz' + artist + album
    cached_data = cache.retrieve(cache_key)

    if cached_data is not None:
        if cached_data == b'magic_no_cover':
            log.info('Returning no cover, from cache')
            return None
        log.info('Returning cover from cache')
        return cached_data

    try:
        release = _search_release_group(artist, album)
        if release is None:
            cache.store(cache_key, b'magic_no_cover')
            return None

        log.info('Found release group %s, downloading image...', release)

        image_bytes = _get_image(release)

        if not image_bytes:
            log.info('Release group has no front cover image')
            cache.store(cache_key, b'magic_no_cover')
            return None

        if not image.check_valid(image_bytes):
            log.warning('Returned image seems to be corrupt')
            return None

        cache.store(cache_key, image_bytes)
        return image_bytes
    except Exception as ex:
        log.info('Error retrieving album art from musicbrainz: %s', ex)
        traceback.print_exc()
        return None

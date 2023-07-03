import logging
import traceback
import urllib

import musicbrainzngs

import cache
import image

musicbrainzngs.set_useragent('Super fancy music player 2.0', 0.1, 'https://github.com/DanielKoomen/WebApp')

log = logging.getLogger('app.musicbrainz')


def _search_release_group(artist: str, title: str) -> str | None:
    """
    Search for a release group id using the provided search query
    """
    log.info('Looking for album release group: %s - %s', artist, title)
    result = musicbrainzngs.search_release_groups(title, artist=artist, limit=1, type='album')
    groups = result['release-group-list']
    if groups:
        log.info('Found release group: %s', groups[0]['id'])
        return groups[0]['id']

    log.info('Looking for single/EP/other release group: %s - %s', artist, title)
    result = musicbrainzngs.search_release_groups(title, artist=artist, limit=1)
    groups = result['release-group-list']
    if groups:
        log.info('Found release group: %s', groups[0]['id'])
        return groups[0]['id']

    log.info('No release group found')
    return None


def _pick_release(release_group: str) -> str | None:
    """
    Choose a release from a release group, to download cover art
    Returns: release id, or None if no suitable release was found
    """
    result = musicbrainzngs.browse_releases(release_group=release_group)
    releases = result['release-list']
    with_artwork = [r for r in releases if r['cover-art-archive']['front'] == 'true']
    if not with_artwork:
        log.warning('No releases with artwork available')
        return None

    # Try to find digital release, it usually has the highest quality cover
    for release in with_artwork:
        if 'packaging' in release and release['packaging'] == 'None':
            log.info('Found packaging==None release: %s', release['id'])
            return release['id']

    log.info('Returning first release in release group')
    return with_artwork[0]['id']


def _get_release_image(release_id: str) -> bytes | None:
    """
    Get album cover URL from MusicBrainz release id
    """
    try:
        return musicbrainzngs.get_image_front(release_id, size="1200")
    except musicbrainzngs.musicbrainz.ResponseError as ex:
        if isinstance(ex.cause, urllib.error.HTTPError) and ex.cause.code == 404:
            return None
        raise ex


def get_cover(artist: str, album: str, disable_cache=False) -> bytes | None:
    """
    Get album cover for the given artist and album
    Returns: Image bytes, or None of no album cover was found.
    """
    cache_key = 'musicbrainz' + artist + album
    cached_data = cache.retrieve(cache_key)

    if cached_data is not None and not disable_cache:
        if cached_data == b'magic_no_cover':
            log.info('Returning no cover, from cache')
            return None
        log.info('Returning cover from cache')
        return cached_data

    try:
        release_group = _search_release_group(artist, album)
        if release_group is None:
            cache.store(cache_key, b'magic_no_cover')
            return None

        release = _pick_release(release_group)

        if release is None:
            return None

        image_bytes = _get_release_image(release)

        if image_bytes is None:
            log.info('Release has no front cover art image image')
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


# For testing
if __name__ == '__main__':
    import logconfig
    logconfig.apply()

    cover = get_cover('London Grammar', 'If You Wait', disable_cache=True)
    with open('cover.jpg', 'wb') as cover_file:
        cover_file.write(cover)

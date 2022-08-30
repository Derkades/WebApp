from typing import Optional

import requests
import musicbrainzngs

import bing


musicbrainzngs.set_useragent('Super fancy music player 2.0', 0.1, 'https://github.com/DanielKoomen/WebApp')


def _search_release(title: str) -> Optional[str]:
    r = musicbrainzngs.search_releases(title)['release-list']
    if len(r) > 0:
        return r[0]['id']
    else:
        return None


def _get_image_url(release_id: str) -> Optional[str]:
    images = musicbrainzngs.get_image_list(release_id)['images']

    for image in images:
        if image['front']:
            return image['image']
    return None

def get_webp_cover(title: str) -> Optional[bytes]:
    release = _search_release(title)
    if release is None:
        return None

    image_url = _get_image_url(release)

    if image_url is None:
        return None

    r = requests.get(image_url)
    image_bytes = r.content
    return bing.webp_thumbnail(image_bytes)


if __name__ == '__main__':
    cover = get_webp_cover('europe - the final countdown')
    with open('musicbrainz_cover_test.webp', 'wb') as f:
        f.truncate(0)
        f.write(cover)
